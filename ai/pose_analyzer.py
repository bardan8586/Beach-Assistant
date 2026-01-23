"""
Pose Analyzer - Extract swimming behavior from body keypoints
============================================================

Uses YOLOv8-Pose to track 17 body keypoints and analyze swimming patterns.

KEY DROWNING INDICATORS:
1. Vertical body position (not horizontal swimming)
2. Arms extended sideways (not stroking)
3. Head tilted back, mouth at water level
4. No leg kick
5. No forward progress despite movement

Instinctive Drowning Response (IDR):
- Lasts 20-60 seconds before submersion
- Body vertical, arms pressing down
- Unable to call for help
- No leg kick visible
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum

# YOLOv8-Pose keypoint indices (COCO format)
class KeyPoint(Enum):
    NOSE = 0
    LEFT_EYE = 1
    RIGHT_EYE = 2
    LEFT_EAR = 3
    RIGHT_EAR = 4
    LEFT_SHOULDER = 5
    RIGHT_SHOULDER = 6
    LEFT_ELBOW = 7
    RIGHT_ELBOW = 8
    LEFT_WRIST = 9
    RIGHT_WRIST = 10
    LEFT_HIP = 11
    RIGHT_HIP = 12
    LEFT_KNEE = 13
    RIGHT_KNEE = 14
    LEFT_ANKLE = 15
    RIGHT_ANKLE = 16


class SwimmingAction(Enum):
    """Swimming action classification"""
    SWIMMING_NORMAL = "swimming_normal"      # Regular swimming strokes
    FLOATING = "floating"                    # Stationary, controlled
    TREADING_WATER = "treading_water"        # Vertical, controlled movement
    STRUGGLING = "struggling"                 # Erratic, vertical, high arm movement
    PASSIVE_DROWNING = "passive_drowning"    # Minimal movement, face down
    ACTIVE_DROWNING = "active_drowning"      # IDR - arms out, vertical, no progress
    UNKNOWN = "unknown"                       # Can't determine


@dataclass
class PoseFeatures:
    """Extracted features from pose for drowning detection"""
    body_angle: float           # 0=horizontal (swimming), 90=vertical (drowning)
    arm_extension_ratio: float  # 0=close to body, 1=extended sideways
    head_tilt_angle: float      # Head orientation
    leg_activity: float         # 0=no kick, 1=active kicking
    vertical_movement: float    # Bobbing up/down (drowning sign)
    forward_progress: float     # Moving forward or stationary?
    arm_stroke_rate: float      # Strokes per second
    body_compactness: float     # Spread out vs compact (panic indicator)
    confidence: float           # Overall pose detection confidence


class PoseAnalyzer:
    """
    Analyzes body pose to detect drowning behavior
    """
    
    def __init__(self):
        self.pose_history = {}  # track_id -> List[PoseFeatures]
        self.max_history = 30   # Keep 30 frames (~3 seconds at 10fps)
        
    def analyze_pose(self, keypoints: np.ndarray, track_id: int) -> Tuple[PoseFeatures, SwimmingAction]:
        """
        Analyze pose keypoints to extract swimming features
        
        Args:
            keypoints: (17, 3) array of [x, y, confidence] for each keypoint
            track_id: Swimmer ID for temporal tracking
            
        Returns:
            (PoseFeatures, SwimmingAction)
        """
        # Extract keypoint positions
        kp = self._extract_keypoints(keypoints)
        
        # Calculate features
        features = PoseFeatures(
            body_angle=self._calculate_body_angle(kp),
            arm_extension_ratio=self._calculate_arm_extension(kp),
            head_tilt_angle=self._calculate_head_tilt(kp),
            leg_activity=self._calculate_leg_activity(kp),
            vertical_movement=self._calculate_vertical_movement(track_id, kp),
            forward_progress=self._calculate_forward_progress(track_id, kp),
            arm_stroke_rate=self._calculate_stroke_rate(track_id, kp),
            body_compactness=self._calculate_body_compactness(kp),
            confidence=self._calculate_pose_confidence(keypoints)
        )
        
        # Store in history
        if track_id not in self.pose_history:
            self.pose_history[track_id] = []
        self.pose_history[track_id].append(features)
        if len(self.pose_history[track_id]) > self.max_history:
            self.pose_history[track_id].pop(0)
        
        # Classify action
        action = self._classify_action(features, self.pose_history.get(track_id, []))
        
        return features, action
    
    def _extract_keypoints(self, keypoints: np.ndarray) -> dict:
        """Extract keypoint positions into dict"""
        kp = {}
        for point in KeyPoint:
            idx = point.value
            if idx < len(keypoints) and keypoints[idx, 2] > 0.3:  # confidence threshold
                kp[point.name] = keypoints[idx, :2]  # x, y
            else:
                kp[point.name] = None
        return kp
    
    def _calculate_body_angle(self, kp: dict) -> float:
        """
        Calculate body angle: 0=horizontal (swimming), 90=vertical (drowning)
        
        Uses shoulder-hip line angle
        """
        try:
            # Get midpoints
            shoulder_y = np.mean([kp['LEFT_SHOULDER'][1], kp['RIGHT_SHOULDER'][1]]) if kp['LEFT_SHOULDER'] is not None and kp['RIGHT_SHOULDER'] is not None else None
            hip_y = np.mean([kp['LEFT_HIP'][1], kp['RIGHT_HIP'][1]]) if kp['LEFT_HIP'] is not None and kp['RIGHT_HIP'] is not None else None
            
            shoulder_x = np.mean([kp['LEFT_SHOULDER'][0], kp['RIGHT_SHOULDER'][0]]) if kp['LEFT_SHOULDER'] is not None and kp['RIGHT_SHOULDER'] is not None else None
            hip_x = np.mean([kp['LEFT_HIP'][0], kp['RIGHT_HIP'][0]]) if kp['LEFT_HIP'] is not None and kp['RIGHT_HIP'] is not None else None
            
            if shoulder_y is not None and hip_y is not None and shoulder_x is not None and hip_x is not None:
                # Calculate angle from horizontal
                dy = hip_y - shoulder_y
                dx = hip_x - shoulder_x
                angle = np.abs(np.degrees(np.arctan2(dy, dx + 1e-6)))
                # Normalize: 0=horizontal, 90=vertical
                return min(angle, 180 - angle)
            else:
                return 45.0  # Unknown, assume mid-range
        except:
            return 45.0
    
    def _calculate_arm_extension(self, kp: dict) -> float:
        """
        Calculate arm extension ratio: 0=close to body, 1=extended sideways
        
        Drowning: arms extended sideways pressing down (IDR)
        Swimming: arms stroking (moving)
        """
        try:
            # Calculate shoulder width
            if kp['LEFT_SHOULDER'] is not None and kp['RIGHT_SHOULDER'] is not None:
                shoulder_width = np.linalg.norm(kp['LEFT_SHOULDER'] - kp['RIGHT_SHOULDER'])
            else:
                return 0.5
            
            # Calculate wrist distance from shoulders
            left_extension = 0.0
            if kp['LEFT_SHOULDER'] is not None and kp['LEFT_WRIST'] is not None:
                left_extension = np.linalg.norm(kp['LEFT_WRIST'] - kp['LEFT_SHOULDER']) / (shoulder_width + 1e-6)
            
            right_extension = 0.0
            if kp['RIGHT_SHOULDER'] is not None and kp['RIGHT_WRIST'] is not None:
                right_extension = np.linalg.norm(kp['RIGHT_WRIST'] - kp['RIGHT_SHOULDER']) / (shoulder_width + 1e-6)
            
            # Average extension, normalized
            return np.clip((left_extension + right_extension) / 2.0, 0, 1)
        except:
            return 0.5
    
    def _calculate_head_tilt(self, kp: dict) -> float:
        """Calculate head tilt angle (drowning: head back, mouth at water)"""
        try:
            if kp['NOSE'] is not None and kp['LEFT_SHOULDER'] is not None and kp['RIGHT_SHOULDER'] is not None:
                shoulder_mid = (kp['LEFT_SHOULDER'] + kp['RIGHT_SHOULDER']) / 2
                dy = kp['NOSE'][1] - shoulder_mid[1]
                dx = kp['NOSE'][0] - shoulder_mid[0]
                return np.degrees(np.arctan2(dy, dx + 1e-6))
            else:
                return 0.0
        except:
            return 0.0
    
    def _calculate_leg_activity(self, kp: dict) -> float:
        """
        Estimate leg activity: 0=no kick, 1=active kicking
        
        Drowning: no visible leg kick (or weak flutter)
        """
        # Simplified: measure distance between knees/ankles
        # In future: use temporal analysis of leg movement
        try:
            if kp['LEFT_KNEE'] is not None and kp['RIGHT_KNEE'] is not None:
                knee_distance = np.linalg.norm(kp['LEFT_KNEE'] - kp['RIGHT_KNEE'])
                # Normalize by body size (shoulder width as proxy)
                if kp['LEFT_SHOULDER'] is not None and kp['RIGHT_SHOULDER'] is not None:
                    shoulder_width = np.linalg.norm(kp['LEFT_SHOULDER'] - kp['RIGHT_SHOULDER'])
                    return np.clip(knee_distance / (shoulder_width + 1e-6), 0, 1)
            return 0.5
        except:
            return 0.5
    
    def _calculate_vertical_movement(self, track_id: int, kp: dict) -> float:
        """
        Calculate vertical bobbing (drowning sign)
        
        Drowning: repeated vertical movement (head going under/emerging)
        """
        if track_id not in self.pose_history or len(self.pose_history[track_id]) < 5:
            return 0.0
        
        try:
            # Get nose Y positions over last 5 frames
            nose_y_history = []
            for hist_features in self.pose_history[track_id][-5:]:
                # Note: we don't have kp in history, simplification needed
                pass
            # Simplified: return 0 for now, will improve with full history
            return 0.0
        except:
            return 0.0
    
    def _calculate_forward_progress(self, track_id: int, kp: dict) -> float:
        """
        Calculate forward movement
        
        Drowning: no forward progress despite arm/leg movement
        """
        # Will implement with full tracking history
        return 0.5
    
    def _calculate_stroke_rate(self, track_id: int, kp: dict) -> float:
        """Calculate arm stroke rate (strokes per second)"""
        # Will implement with temporal analysis
        return 0.0
    
    def _calculate_body_compactness(self, kp: dict) -> float:
        """
        Calculate how spread out the body is
        
        Panic: body spread out (arms/legs extended)
        Calm: body compact
        """
        try:
            positions = [pos for pos in kp.values() if pos is not None]
            if len(positions) < 4:
                return 0.5
            
            positions = np.array(positions)
            std = np.std(positions, axis=0)
            return np.clip(np.mean(std) / 100.0, 0, 1)  # Normalize
        except:
            return 0.5
    
    def _calculate_pose_confidence(self, keypoints: np.ndarray) -> float:
        """Calculate overall pose detection confidence"""
        confidences = keypoints[:, 2]
        return np.mean(confidences[confidences > 0.3])
    
    def _classify_action(self, features: PoseFeatures, history: List[PoseFeatures]) -> SwimmingAction:
        """
        Classify swimming action based on pose features
        
        CRITICAL: Detect drowning patterns
        """
        # ACTIVE DROWNING (Instinctive Drowning Response)
        # - Vertical body (>60 degrees)
        # - Arms extended sideways
        # - No forward progress
        # - Low leg activity
        if (features.body_angle > 60 and 
            features.arm_extension_ratio > 0.6 and 
            features.forward_progress < 0.2 and 
            features.leg_activity < 0.3):
            return SwimmingAction.ACTIVE_DROWNING
        
        # PASSIVE DROWNING
        # - Face down (horizontal but no movement)
        # - Low arm/leg activity
        # - No progress
        if (features.body_angle < 30 and 
            features.arm_extension_ratio < 0.3 and 
            features.leg_activity < 0.2 and 
            features.forward_progress < 0.1):
            return SwimmingAction.PASSIVE_DROWNING
        
        # STRUGGLING
        # - Erratic movement (high body compactness variance)
        # - Vertical position
        # - Some arm activity but inefficient
        if (features.body_angle > 50 and 
            features.arm_extension_ratio > 0.4 and 
            features.body_compactness > 0.6):
            return SwimmingAction.STRUGGLING
        
        # TREADING WATER
        # - Vertical position but controlled
        # - Moderate arm/leg activity
        # - Minimal forward progress
        if (features.body_angle > 50 and 
            features.leg_activity > 0.4 and 
            features.forward_progress < 0.3):
            return SwimmingAction.TREADING_WATER
        
        # FLOATING
        # - Horizontal or slightly tilted
        # - Low movement
        # - Stationary
        if (features.body_angle < 40 and 
            features.leg_activity < 0.3 and 
            features.forward_progress < 0.2):
            return SwimmingAction.FLOATING
        
        # SWIMMING NORMAL
        # - Horizontal body
        # - Moderate-high arm activity
        # - Forward progress
        if (features.body_angle < 40 and 
            features.arm_extension_ratio > 0.3 and 
            features.forward_progress > 0.3):
            return SwimmingAction.SWIMMING_NORMAL
        
        return SwimmingAction.UNKNOWN
    
    def get_drowning_risk_from_pose(self, action: SwimmingAction, features: PoseFeatures) -> float:
        """
        Calculate drowning risk score from pose analysis (0-100)
        """
        if action == SwimmingAction.ACTIVE_DROWNING:
            return 95.0  # CRITICAL
        elif action == SwimmingAction.PASSIVE_DROWNING:
            return 90.0  # CRITICAL
        elif action == SwimmingAction.STRUGGLING:
            return 70.0  # HIGH
        elif action == SwimmingAction.TREADING_WATER:
            # Depends on duration (will add temporal component)
            return 30.0  # MEDIUM
        elif action == SwimmingAction.FLOATING:
            return 20.0  # LOW (could be resting)
        elif action == SwimmingAction.SWIMMING_NORMAL:
            return 5.0   # LOW
        else:
            return 10.0  # UNKNOWN
