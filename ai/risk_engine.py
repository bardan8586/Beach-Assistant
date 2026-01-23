"""
Risk Engine
===========
Calculates risk scores for swimmers and generates alerts.

Risk factors:
- Stationary for too long
- In danger zone
- Erratic movement
- Rapid movement away from shore
- Time in water
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time

from water_analyzer import WaterZone
from behavior_analyzer import MovementPattern, MotionMetrics


class RiskLevel(Enum):
    """Risk level categories"""
    LOW = "low"          # 0-30
    MEDIUM = "medium"    # 31-70
    HIGH = "high"        # 71-100


@dataclass
class RiskScore:
    """Risk score for a swimmer"""
    track_id: int
    total_score: float  # 0-100
    level: RiskLevel
    factors: Dict[str, float]  # Individual risk factor scores
    timestamp: float
    alert_triggered: bool = False


class RiskEngine:
    """
    Calculates risk scores and generates alerts.
    """
    
    def __init__(
        self,
        stationary_risk_weight: float = 40.0,  # High weight for stationary
        danger_zone_risk_weight: float = 30.0,
        erratic_risk_weight: float = 20.0,
        rapid_away_risk_weight: float = 25.0,
        time_risk_weight: float = 15.0,
        alert_threshold: float = 70.0,  # Alert if score >= 70
        warning_threshold: float = 50.0,  # Warning if score >= 50
    ):
        """
        Initialize risk engine.
        
        Args:
            stationary_risk_weight: Risk score for stationary behavior
            danger_zone_risk_weight: Risk score for being in danger zone
            erratic_risk_weight: Risk score for erratic movement
            rapid_away_risk_weight: Risk score for rapid movement away from shore
            time_risk_weight: Risk score for long time in water
            alert_threshold: Score threshold for critical alert
            warning_threshold: Score threshold for warning
        """
        self.stationary_risk_weight = stationary_risk_weight
        self.danger_zone_risk_weight = danger_zone_risk_weight
        self.erratic_risk_weight = erratic_risk_weight
        self.rapid_away_risk_weight = rapid_away_risk_weight
        self.time_risk_weight = time_risk_weight
        self.alert_threshold = alert_threshold
        self.warning_threshold = warning_threshold
        
        # Track risk scores: track_id -> RiskScore
        self.risk_scores: Dict[int, RiskScore] = {}
        
        # Track alert history: track_id -> last alert timestamp
        self.alert_history: Dict[int, float] = {}
        self.alert_cooldown = 30.0  # Don't alert same track more than once per 30 seconds
    
    def calculate_risk(
        self,
        track_id: int,
        zone: WaterZone,
        motion_metrics: MotionMetrics,
        distance_from_shore: float,
        timestamp: float,
        pose_risk_override: Optional[float] = None  # NEW: Pose-based drowning risk
    ) -> RiskScore:
        """
        Calculate risk score for a swimmer.
        
        Args:
            track_id: Track ID
            zone: Current water zone
            motion_metrics: Motion analysis metrics
            distance_from_shore: Distance from shore in pixels
            timestamp: Current timestamp
            pose_risk_override: If provided, use this as primary risk score (drowning detection)
            
        Returns:
            RiskScore object
        """
        factors = {}
        total_score = 0.0
        
        # 🚨 PRIORITY: Pose-based drowning detection (overrides other factors)
        if pose_risk_override is not None and pose_risk_override > 50:
            # HIGH CONFIDENCE drowning behavior detected from pose
            factors["pose_drowning_detection"] = pose_risk_override
            total_score = pose_risk_override
            
            # Determine risk level
            if total_score >= 90:
                level = RiskLevel.HIGH  # CRITICAL drowning
            elif total_score >= 70:
                level = RiskLevel.HIGH
            elif total_score >= 50:
                level = RiskLevel.MEDIUM
            else:
                level = RiskLevel.LOW
            
            # Immediate alert for drowning behavior (no cooldown for critical)
            alert_triggered = False
            if total_score >= self.alert_threshold:
                alert_triggered = True
                self.alert_history[track_id] = timestamp
            
            risk_score = RiskScore(
                track_id=track_id,
                total_score=total_score,
                level=level,
                factors=factors,
                timestamp=timestamp,
                alert_triggered=alert_triggered
            )
            
            self.risk_scores[track_id] = risk_score
            return risk_score
        
        # Factor 1: Stationary behavior
        if motion_metrics.pattern == MovementPattern.STATIONARY:
            # Increase risk based on time stationary
            stationary_time = motion_metrics.time_in_view
            if stationary_time > 30:  # More than 30 seconds
                stationary_score = min(self.stationary_risk_weight * (stationary_time / 60), 
                                      self.stationary_risk_weight)
                factors["stationary"] = stationary_score
                total_score += stationary_score
        
        # Factor 2: Danger zone
        if zone == WaterZone.DANGER:
            factors["danger_zone"] = self.danger_zone_risk_weight
            total_score += self.danger_zone_risk_weight
        elif zone == WaterZone.CAUTION:
            factors["caution_zone"] = self.danger_zone_risk_weight * 0.5
            total_score += self.danger_zone_risk_weight * 0.5
        
        # Factor 3: Erratic movement
        if motion_metrics.pattern == MovementPattern.ERRATIC:
            factors["erratic"] = self.erratic_risk_weight
            total_score += self.erratic_risk_weight
        
        # Factor 4: Rapid movement away from shore
        if motion_metrics.pattern == MovementPattern.RAPID:
            # Check if moving away from shore (positive velocity_y means moving up/away)
            if motion_metrics.velocity_y < -10:  # Moving away (negative y in image coords)
                factors["rapid_away"] = self.rapid_away_risk_weight
                total_score += self.rapid_away_risk_weight
        
        # Factor 5: Time in water (longer = slightly higher risk)
        if motion_metrics.time_in_view > 120:  # More than 2 minutes
            time_score = min(self.time_risk_weight * ((motion_metrics.time_in_view - 120) / 60),
                           self.time_risk_weight)
            factors["time_in_water"] = time_score
            total_score += time_score
        
        # Cap total score at 100
        total_score = min(total_score, 100.0)
        
        # Determine risk level
        if total_score >= self.alert_threshold:
            level = RiskLevel.HIGH
        elif total_score >= self.warning_threshold:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW
        
        # Check if we should trigger alert
        alert_triggered = False
        if total_score >= self.alert_threshold:
            # Check cooldown
            last_alert = self.alert_history.get(track_id, 0)
            if timestamp - last_alert > self.alert_cooldown:
                alert_triggered = True
                self.alert_history[track_id] = timestamp
        
        risk_score = RiskScore(
            track_id=track_id,
            total_score=total_score,
            level=level,
            factors=factors,
            timestamp=timestamp,
            alert_triggered=alert_triggered
        )
        
        self.risk_scores[track_id] = risk_score
        return risk_score
    
    def get_risk_score(self, track_id: int) -> Optional[RiskScore]:
        """
        Get current risk score for a track.
        
        Args:
            track_id: Track ID
            
        Returns:
            RiskScore or None if not found
        """
        return self.risk_scores.get(track_id)
    
    def get_active_alerts(self) -> List[RiskScore]:
        """
        Get all active high-risk alerts.
        
        Returns:
            List of RiskScore objects with HIGH level
        """
        return [score for score in self.risk_scores.values() 
                if score.level == RiskLevel.HIGH]
    
    def cleanup(self, active_track_ids: List[int]):
        """
        Remove risk scores for tracks that are no longer active.
        
        Args:
            active_track_ids: List of currently active track IDs
        """
        active_set = set(active_track_ids)
        to_remove = [tid for tid in self.risk_scores.keys() if tid not in active_set]
        
        for tid in to_remove:
            self.risk_scores.pop(tid, None)
            self.alert_history.pop(tid, None)

