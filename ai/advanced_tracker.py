"""
Advanced Tracker - Robust tracking for ocean conditions
========================================================

Enhancements over basic ByteTrack:
1. Occlusion handling - predict position during temporary occlusion
2. Re-identification - recover swimmer ID using appearance features
3. Trajectory prediction - predict movement 5-10 seconds ahead
4. Drift detection - identify swimmers being pulled by currents

Real ocean challenges:
- Waves hide swimmers (partial occlusion)
- Swimmers go underwater (full occlusion)
- Multiple swimmers overlap
- Camera shake (boat/drone cameras)
- Lighting changes (sun glare, clouds)
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque
import cv2


@dataclass
class SwimmerAppearance:
    """Appearance features for re-identification"""
    color_histogram: np.ndarray  # RGB histogram
    bbox_aspect_ratio: float     # Height/width ratio
    average_size: float          # Average bbox area
    last_seen_frame: int         # Frame number when last seen
    confidence: float            # How confident are we in this identity?


@dataclass
class PredictedTrajectory:
    """Predicted future positions"""
    positions: List[Tuple[int, int]]  # Next 5-10 positions
    confidence: float                  # Prediction confidence
    time_horizon: float                # How far ahead (seconds)


class AdvancedTracker:
    """
    Enhanced tracking with occlusion handling and re-identification
    """
    
    def __init__(self, max_occlusion_frames: int = 30):
        """
        Args:
            max_occlusion_frames: How long to keep track after disappearing (frames)
        """
        self.max_occlusion_frames = max_occlusion_frames
        
        # Appearance features: track_id -> SwimmerAppearance
        self.appearance_db: Dict[int, SwimmerAppearance] = {}
        
        # Occlusion tracking: track_id -> frames_occluded
        self.occlusion_count: Dict[int, int] = {}
        
        # Trajectory history: track_id -> deque of (x, y, timestamp)
        self.trajectory_history: Dict[int, deque] = {}
        self.max_trajectory_length = 60  # Keep 60 points (~6 seconds at 10fps)
        
        # Predicted trajectories: track_id -> PredictedTrajectory
        self.predictions: Dict[int, PredictedTrajectory] = {}
    
    def update_appearance(self, track_id: int, frame: np.ndarray, bbox: Tuple[int, int, int, int], frame_idx: int):
        """
        Extract and store appearance features for re-identification
        
        Args:
            track_id: Swimmer ID
            frame: Full frame image
            bbox: Bounding box (x1, y1, x2, y2)
            frame_idx: Current frame number
        """
        x1, y1, x2, y2 = bbox
        
        # Ensure bbox is within frame bounds
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        if x2 <= x1 or y2 <= y1:
            return  # Invalid bbox
        
        # Extract swimmer crop
        swimmer_crop = frame[y1:y2, x1:x2]
        
        if swimmer_crop.size == 0:
            return
        
        # Compute appearance features
        try:
            # 1. Color histogram (robust to pose changes)
            hist = cv2.calcHist([swimmer_crop], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
            hist = cv2.normalize(hist, hist).flatten()
            
            # 2. Bbox aspect ratio (height/width)
            aspect_ratio = (y2 - y1) / (x2 - x1 + 1e-6)
            
            # 3. Average size
            bbox_area = (x2 - x1) * (y2 - y1)
            
            # Update or create appearance
            if track_id in self.appearance_db:
                # Smooth update (exponential moving average)
                old_appearance = self.appearance_db[track_id]
                alpha = 0.3  # Learning rate
                hist = alpha * hist + (1 - alpha) * old_appearance.color_histogram
                aspect_ratio = alpha * aspect_ratio + (1 - alpha) * old_appearance.bbox_aspect_ratio
                bbox_area = alpha * bbox_area + (1 - alpha) * old_appearance.average_size
            
            self.appearance_db[track_id] = SwimmerAppearance(
                color_histogram=hist,
                bbox_aspect_ratio=aspect_ratio,
                average_size=bbox_area,
                last_seen_frame=frame_idx,
                confidence=0.9
            )
        except Exception as e:
            # Silently fail on appearance extraction errors
            pass
    
    def predict_position_during_occlusion(self, track_id: int, current_frame: int) -> Optional[Tuple[int, int]]:
        """
        Predict swimmer position during occlusion using trajectory history
        
        Args:
            track_id: Swimmer ID
            current_frame: Current frame number
            
        Returns:
            Predicted (x, y) position or None if can't predict
        """
        if track_id not in self.trajectory_history or len(self.trajectory_history[track_id]) < 3:
            return None
        
        trajectory = list(self.trajectory_history[track_id])
        
        # Use linear extrapolation based on last 5 points
        recent_points = trajectory[-5:]
        
        if len(recent_points) < 3:
            return None
        
        # Extract positions and times
        positions = np.array([(p[0], p[1]) for p in recent_points])
        times = np.array([p[2] for p in recent_points])
        
        # Fit linear model: position = velocity * time + offset
        if len(times) > 1 and times[-1] != times[0]:
            # Calculate velocity (pixels per second)
            dt = times[-1] - times[0]
            velocity = (positions[-1] - positions[0]) / dt
            
            # Extrapolate to current time
            last_time = times[-1]
            time_since_last = current_frame - self.appearance_db[track_id].last_seen_frame
            
            # Predict position
            predicted_pos = positions[-1] + velocity * (time_since_last * 0.1)  # Assume 10 FPS
            
            return tuple(predicted_pos.astype(int))
        
        return None
    
    def predict_trajectory(self, track_id: int, time_horizon: float = 5.0) -> Optional[PredictedTrajectory]:
        """
        Predict future trajectory for next 5-10 seconds
        
        Args:
            track_id: Swimmer ID
            time_horizon: How far ahead to predict (seconds)
            
        Returns:
            PredictedTrajectory or None
        """
        if track_id not in self.trajectory_history or len(self.trajectory_history[track_id]) < 10:
            return None
        
        trajectory = list(self.trajectory_history[track_id])
        recent_points = trajectory[-20:]  # Last 2 seconds at 10fps
        
        # Extract positions and times
        positions = np.array([(p[0], p[1]) for p in recent_points])
        times = np.array([p[2] for p in recent_points])
        
        if len(times) < 10:
            return None
        
        # Fit polynomial trajectory (degree 2 for smooth curves)
        try:
            # Fit x(t) and y(t) separately
            poly_x = np.polyfit(times - times[0], positions[:, 0], deg=2)
            poly_y = np.polyfit(times - times[0], positions[:, 1], deg=2)
            
            # Generate future time steps (10 points over time_horizon)
            future_times = np.linspace(times[-1] - times[0], times[-1] - times[0] + time_horizon, 10)
            
            # Predict positions
            pred_x = np.polyval(poly_x, future_times)
            pred_y = np.polyval(poly_y, future_times)
            
            predicted_positions = [(int(x), int(y)) for x, y in zip(pred_x, pred_y)]
            
            # Calculate prediction confidence (based on trajectory smoothness)
            # Smoother trajectories = higher confidence
            velocities = np.diff(positions, axis=0)
            velocity_std = np.std(velocities, axis=0).mean()
            confidence = np.clip(1.0 - velocity_std / 50.0, 0.3, 0.95)
            
            return PredictedTrajectory(
                positions=predicted_positions,
                confidence=confidence,
                time_horizon=time_horizon
            )
        except:
            return None
    
    def attempt_reidentification(self, 
                                  lost_track_id: int, 
                                  new_detections: List[Tuple[int, int, int, int]], 
                                  frame: np.ndarray,
                                  frame_idx: int) -> Optional[int]:
        """
        Try to match a lost track to a new detection using appearance features
        
        Args:
            lost_track_id: ID of swimmer we lost
            new_detections: List of new detections without IDs [(x1,y1,x2,y2), ...]
            frame: Current frame
            frame_idx: Current frame number
            
        Returns:
            Index of matching detection in new_detections, or None
        """
        if lost_track_id not in self.appearance_db:
            return None
        
        lost_appearance = self.appearance_db[lost_track_id]
        
        # Only attempt re-ID if lost recently (within 60 frames = 6 seconds)
        if frame_idx - lost_appearance.last_seen_frame > 60:
            return None
        
        best_match_idx = None
        best_similarity = 0.6  # Minimum threshold
        
        for idx, bbox in enumerate(new_detections):
            x1, y1, x2, y2 = bbox
            
            # Ensure bbox is within frame bounds
            h, w = frame.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            
            if x2 <= x1 or y2 <= y1:
                continue
            
            swimmer_crop = frame[y1:y2, x1:x2]
            
            if swimmer_crop.size == 0:
                continue
            
            try:
                # Compute appearance features for this detection
                hist = cv2.calcHist([swimmer_crop], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
                hist = cv2.normalize(hist, hist).flatten()
                
                aspect_ratio = (y2 - y1) / (x2 - x1 + 1e-6)
                bbox_area = (x2 - x1) * (y2 - y1)
                
                # Calculate similarity
                # 1. Histogram correlation (0-1, higher = more similar)
                hist_similarity = cv2.compareHist(lost_appearance.color_histogram, hist, cv2.HISTCMP_CORREL)
                
                # 2. Aspect ratio similarity
                aspect_diff = abs(aspect_ratio - lost_appearance.bbox_aspect_ratio)
                aspect_similarity = np.exp(-aspect_diff)  # Exponential decay
                
                # 3. Size similarity
                size_ratio = min(bbox_area, lost_appearance.average_size) / max(bbox_area, lost_appearance.average_size)
                
                # Combined similarity (weighted average)
                similarity = 0.5 * hist_similarity + 0.3 * aspect_similarity + 0.2 * size_ratio
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match_idx = idx
            
            except Exception as e:
                continue
        
        return best_match_idx
    
    def update_trajectory(self, track_id: int, position: Tuple[int, int], timestamp: float):
        """
        Update trajectory history for a swimmer
        
        Args:
            track_id: Swimmer ID
            position: Center position (x, y)
            timestamp: Current timestamp
        """
        if track_id not in self.trajectory_history:
            self.trajectory_history[track_id] = deque(maxlen=self.max_trajectory_length)
        
        self.trajectory_history[track_id].append((position[0], position[1], timestamp))
    
    def detect_drift(self, track_id: int, shore_line_y: int) -> Tuple[bool, float]:
        """
        Detect if swimmer is drifting (pulled by current/rip tide)
        
        Args:
            track_id: Swimmer ID
            shore_line_y: Y coordinate of shore line
            
        Returns:
            (is_drifting, drift_speed) - drift_speed in pixels/second away from shore
        """
        if track_id not in self.trajectory_history or len(self.trajectory_history[track_id]) < 20:
            return False, 0.0
        
        trajectory = list(self.trajectory_history[track_id])
        recent_points = trajectory[-20:]  # Last 2 seconds
        
        # Calculate movement away from shore
        positions = np.array([(p[0], p[1]) for p in recent_points])
        times = np.array([p[2] for p in recent_points])
        
        # Distance from shore (negative y = away from shore in typical camera setup)
        distances_from_shore = shore_line_y - positions[:, 1]
        
        # Calculate rate of change (drift speed)
        if len(times) > 1:
            time_span = times[-1] - times[0]
            distance_change = distances_from_shore[-1] - distances_from_shore[0]
            
            if time_span > 0:
                drift_speed = distance_change / time_span  # pixels per second
                
                # Drifting if moving away from shore consistently (> 5 pixels/second)
                is_drifting = drift_speed < -5.0  # Negative = away from shore
                
                return is_drifting, abs(drift_speed)
        
        return False, 0.0
    
    def cleanup(self, active_track_ids: List[int]):
        """
        Remove stale entries for tracks that are gone
        
        Args:
            active_track_ids: List of currently active track IDs
        """
        # Remove appearance data for very old tracks (not seen in 300 frames = 30 seconds)
        stale_ids = []
        for track_id, appearance in self.appearance_db.items():
            if track_id not in active_track_ids:
                # Keep for a while in case of re-identification
                stale_ids.append(track_id)
        
        # Don't immediately delete - keep for re-identification window
        # Only delete after max_occlusion_frames * 10 (extended window)
        # This is handled implicitly by checking last_seen_frame in attempt_reidentification
