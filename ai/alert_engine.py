"""
Alert Engine - Trustworthy, Non-Spammy Alerts
==============================================

Purpose: Generate alerts that lifeguards can trust and act on

Key Features:
1. Hysteresis - Risk must stay high for X seconds before alerting
2. Throttling - Max N alerts per swimmer per time window
3. Escalation - WATCH → ALERT → EMERGENCY progression
4. Deduplication - Don't alert twice for same issue
5. Context - Provide actionable information
6. Feedback Loop - Learn from false alarms

Alert Levels:
- WATCH (🟡): Elevated risk, monitor closely (50-70 risk score)
- ALERT (🟠): High risk, prepare response (70-90 risk score)
- EMERGENCY (🔴): Critical, immediate action (90+ risk score)

Design Philosophy:
- "Better to alert late than to cry wolf"
- "One good alert > ten false alarms"
- "Context > Volume"
"""

import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque


class AlertLevel(Enum):
    """Alert severity levels"""
    WATCH = "watch"           # 🟡 Monitor closely
    ALERT = "alert"           # 🟠 Prepare response
    EMERGENCY = "emergency"   # 🔴 Immediate action


class AlertReason(Enum):
    """Why are we alerting?"""
    DROWNING_BEHAVIOR = "drowning_behavior"      # Pose detected drowning
    PROLONGED_STRUGGLE = "prolonged_struggle"     # Struggling for 20+ seconds
    FATIGUE_CRITICAL = "fatigue_critical"         # Extreme fatigue detected
    DRIFT_DANGER = "drift_danger"                 # Being pulled by rip current
    STATIONARY_SUBMERGED = "stationary_submerged" # Not moving, face down
    PANIC_PROGRESSION = "panic_progression"       # Advanced panic state
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"     # Unusual for this beach


@dataclass
class Alert:
    """Single alert instance"""
    alert_id: str                    # Unique ID
    swimmer_id: int                  # Track ID
    level: AlertLevel                # Severity
    reason: AlertReason              # Why alerting
    risk_score: float                # Current risk (0-100)
    timestamp: float                 # When alert triggered
    location: Tuple[int, int]        # (x, y) position
    zone: str                        # Water zone
    duration: float                  # How long issue has persisted (seconds)
    confidence: float                # Alert confidence (0-1)
    context: str                     # Human-readable context
    action_recommended: str          # What should lifeguard do?
    acknowledged: bool = False       # Has lifeguard seen it?
    resolved: bool = False           # Is issue resolved?
    false_alarm: bool = False        # Marked as false alarm?


@dataclass
class AlertHistory:
    """Track alert history per swimmer"""
    swimmer_id: int
    alerts: List[Alert] = field(default_factory=list)
    last_alert_time: float = 0.0
    total_alerts: int = 0
    false_alarms: int = 0
    
    
class AlertEngine:
    """
    Intelligent alert generation with hysteresis and throttling
    """
    
    def __init__(self):
        # Hysteresis settings (risk must stay high for X seconds)
        self.WATCH_HYSTERESIS = 5.0      # 5 seconds at 50+ risk
        self.ALERT_HYSTERESIS = 8.0      # 8 seconds at 70+ risk
        self.EMERGENCY_HYSTERESIS = 3.0   # 3 seconds at 90+ risk (faster!)
        
        # Throttling settings (max alerts per time window)
        self.ALERT_COOLDOWN = 30.0       # Min 30 seconds between alerts for same swimmer
        self.EMERGENCY_COOLDOWN = 10.0   # Emergency can re-alert faster
        
        # Risk thresholds
        self.WATCH_THRESHOLD = 50
        self.ALERT_THRESHOLD = 70
        self.EMERGENCY_THRESHOLD = 90
        
        # State tracking: swimmer_id -> (risk_level, start_time, peak_risk)
        self.high_risk_state: Dict[int, Tuple[str, float, float]] = {}
        
        # Alert history: swimmer_id -> AlertHistory
        self.alert_history: Dict[int, AlertHistory] = {}
        
        # Active alerts (not yet acknowledged)
        self.active_alerts: Dict[str, Alert] = {}  # alert_id -> Alert
        
        # Alert counter for unique IDs
        self.alert_counter = 0
    
    def update(self,
               swimmer_id: int,
               risk_score: float,
               risk_level: str,
               swimmer_state: str,
               reason: str,
               location: Tuple[int, int],
               zone: str,
               timestamp: float,
               pose_action: Optional[str] = None) -> Optional[Alert]:
        """
        Update alert state for a swimmer
        
        Args:
            swimmer_id: Swimmer ID
            risk_score: Current risk score (0-100)
            risk_level: Risk level string ("low", "medium", "high")
            swimmer_state: Temporal state ("normal", "tiring", "struggling", etc.)
            reason: Primary risk reason
            location: (x, y) position
            zone: Water zone
            timestamp: Current time
            pose_action: Pose-based action if available
            
        Returns:
            Alert if one should be triggered, None otherwise
        """
        # Initialize history if needed
        if swimmer_id not in self.alert_history:
            self.alert_history[swimmer_id] = AlertHistory(swimmer_id=swimmer_id)
        
        history = self.alert_history[swimmer_id]
        
        # Determine if we should alert based on risk score
        should_alert = False
        alert_level = None
        hysteresis_time = 0
        
        # Check thresholds with hysteresis
        if risk_score >= self.EMERGENCY_THRESHOLD:
            alert_level = AlertLevel.EMERGENCY
            hysteresis_time = self.EMERGENCY_HYSTERESIS
            should_alert = True
        elif risk_score >= self.ALERT_THRESHOLD:
            alert_level = AlertLevel.ALERT
            hysteresis_time = self.ALERT_HYSTERESIS
            should_alert = True
        elif risk_score >= self.WATCH_THRESHOLD:
            alert_level = AlertLevel.WATCH
            hysteresis_time = self.WATCH_HYSTERESIS
            should_alert = True
        
        if not should_alert:
            # Risk dropped, clear high-risk state
            if swimmer_id in self.high_risk_state:
                del self.high_risk_state[swimmer_id]
            return None
        
        # Check hysteresis (has risk been high long enough?)
        if swimmer_id in self.high_risk_state:
            prev_level, start_time, peak_risk = self.high_risk_state[swimmer_id]
            duration = timestamp - start_time
            
            # Update peak risk
            if risk_score > peak_risk:
                self.high_risk_state[swimmer_id] = (alert_level.value, start_time, risk_score)
            
            # Check if we've exceeded hysteresis time
            if duration >= hysteresis_time:
                # Check throttling (cooldown period)
                time_since_last_alert = timestamp - history.last_alert_time
                
                cooldown = self.EMERGENCY_COOLDOWN if alert_level == AlertLevel.EMERGENCY else self.ALERT_COOLDOWN
                
                if time_since_last_alert >= cooldown:
                    # TRIGGER ALERT!
                    alert = self._create_alert(
                        swimmer_id=swimmer_id,
                        level=alert_level,
                        risk_score=risk_score,
                        swimmer_state=swimmer_state,
                        reason=reason,
                        location=location,
                        zone=zone,
                        duration=duration,
                        timestamp=timestamp,
                        pose_action=pose_action
                    )
                    
                    # Record alert
                    history.alerts.append(alert)
                    history.last_alert_time = timestamp
                    history.total_alerts += 1
                    
                    # Add to active alerts
                    self.active_alerts[alert.alert_id] = alert
                    
                    # Reset high-risk state (to require new hysteresis for next alert)
                    del self.high_risk_state[swimmer_id]
                    
                    return alert
                else:
                    # Still in cooldown, don't alert yet
                    return None
            else:
                # Still building up hysteresis time
                return None
        else:
            # First time seeing high risk, start hysteresis timer
            self.high_risk_state[swimmer_id] = (alert_level.value, timestamp, risk_score)
            return None
    
    def _create_alert(self,
                      swimmer_id: int,
                      level: AlertLevel,
                      risk_score: float,
                      swimmer_state: str,
                      reason: str,
                      location: Tuple[int, int],
                      zone: str,
                      duration: float,
                      timestamp: float,
                      pose_action: Optional[str]) -> Alert:
        """Create alert with context and recommendations"""
        
        self.alert_counter += 1
        alert_id = f"ALERT-{swimmer_id}-{self.alert_counter}-{int(timestamp)}"
        
        # Map reason to AlertReason enum
        alert_reason = self._map_reason(swimmer_state, pose_action, reason)
        
        # Generate context message
        context = self._generate_context(
            swimmer_id=swimmer_id,
            level=level,
            swimmer_state=swimmer_state,
            duration=duration,
            zone=zone,
            pose_action=pose_action
        )
        
        # Generate action recommendation
        action = self._generate_action_recommendation(level, alert_reason, zone)
        
        # Calculate confidence
        confidence = self._calculate_alert_confidence(
            risk_score=risk_score,
            duration=duration,
            pose_action=pose_action
        )
        
        return Alert(
            alert_id=alert_id,
            swimmer_id=swimmer_id,
            level=level,
            reason=alert_reason,
            risk_score=risk_score,
            timestamp=timestamp,
            location=location,
            zone=zone,
            duration=duration,
            confidence=confidence,
            context=context,
            action_recommended=action
        )
    
    def _map_reason(self, swimmer_state: str, pose_action: Optional[str], reason: str) -> AlertReason:
        """Map state/action to alert reason"""
        if pose_action:
            if "DROWNING" in pose_action.upper():
                return AlertReason.DROWNING_BEHAVIOR
        
        if "drowning" in swimmer_state.lower():
            return AlertReason.DROWNING_BEHAVIOR
        elif "struggling" in swimmer_state.lower() or "critical" in swimmer_state.lower():
            return AlertReason.PROLONGED_STRUGGLE
        elif "tiring" in swimmer_state.lower() or "fatigue" in reason.lower():
            return AlertReason.FATIGUE_CRITICAL
        elif "drift" in reason.lower():
            return AlertReason.DRIFT_DANGER
        elif "stationary" in reason.lower():
            return AlertReason.STATIONARY_SUBMERGED
        else:
            return AlertReason.PANIC_PROGRESSION
    
    def _generate_context(self,
                          swimmer_id: int,
                          level: AlertLevel,
                          swimmer_state: str,
                          duration: float,
                          zone: str,
                          pose_action: Optional[str]) -> str:
        """Generate human-readable context"""
        
        state_descriptions = {
            "drowning": "showing drowning behavior",
            "critical": "in critical struggling state",
            "struggling": "struggling to stay afloat",
            "tiring": "showing signs of fatigue",
        }
        
        state_desc = state_descriptions.get(swimmer_state.lower(), f"in {swimmer_state} state")
        
        context = f"Swimmer #{swimmer_id} {state_desc} for {duration:.0f} seconds in {zone.upper()} zone"
        
        if pose_action and "DROWNING" in pose_action.upper():
            context += f" - POSE ANALYSIS CONFIRMS: {pose_action}"
        
        return context
    
    def _generate_action_recommendation(self, level: AlertLevel, reason: AlertReason, zone: str) -> str:
        """Generate actionable recommendation"""
        
        if level == AlertLevel.EMERGENCY:
            if reason == AlertReason.DROWNING_BEHAVIOR:
                return "🚨 IMMEDIATE WATER RESCUE - Drowning behavior detected"
            else:
                return "🚨 IMMEDIATE ATTENTION - Dispatch lifeguard now"
        
        elif level == AlertLevel.ALERT:
            if zone.upper() == "DANGER":
                return "⚠️ PREPARE RESCUE EQUIPMENT - High risk in danger zone"
            else:
                return "⚠️ VISUAL CONTACT - Watch closely, prepare to respond"
        
        else:  # WATCH
            return "👁️ MONITOR - Elevated risk, maintain visual contact"
    
    def _calculate_alert_confidence(self,
                                     risk_score: float,
                                     duration: float,
                                     pose_action: Optional[str]) -> float:
        """Calculate confidence in alert (0-1)"""
        
        confidence = 0.5  # Base
        
        # Higher risk = higher confidence
        if risk_score > 90:
            confidence += 0.3
        elif risk_score > 70:
            confidence += 0.2
        
        # Longer duration = higher confidence
        if duration > 20:
            confidence += 0.2
        elif duration > 10:
            confidence += 0.1
        
        # Pose confirmation = higher confidence
        if pose_action and "DROWNING" in pose_action.upper():
            confidence += 0.3
        
        return min(1.0, confidence)
    
    def acknowledge_alert(self, alert_id: str, timestamp: float) -> bool:
        """
        Mark alert as acknowledged by lifeguard
        
        Returns:
            True if acknowledged, False if alert not found
        """
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            return True
        return False
    
    def resolve_alert(self, alert_id: str, timestamp: float) -> bool:
        """
        Mark alert as resolved (issue no longer present)
        
        Returns:
            True if resolved, False if alert not found
        """
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            # Remove from active alerts
            del self.active_alerts[alert_id]
            return True
        return False
    
    def mark_false_alarm(self, alert_id: str) -> bool:
        """
        Mark alert as false alarm (for learning)
        
        Returns:
            True if marked, False if alert not found
        """
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.false_alarm = True
            
            # Update history
            if alert.swimmer_id in self.alert_history:
                self.alert_history[alert.swimmer_id].false_alarms += 1
            
            # Remove from active
            del self.active_alerts[alert_id]
            return True
        return False
    
    def get_active_alerts(self, level: Optional[AlertLevel] = None) -> List[Alert]:
        """
        Get all active (unacknowledged/unresolved) alerts
        
        Args:
            level: Filter by level (None = all levels)
            
        Returns:
            List of active alerts, sorted by severity then timestamp
        """
        alerts = list(self.active_alerts.values())
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        # Sort by severity (emergency first) then timestamp (oldest first)
        severity_order = {AlertLevel.EMERGENCY: 0, AlertLevel.ALERT: 1, AlertLevel.WATCH: 2}
        alerts.sort(key=lambda a: (severity_order[a.level], a.timestamp))
        
        return alerts
    
    def get_alert_summary(self) -> Dict[str, int]:
        """Get count of alerts by level"""
        summary = {
            "emergency": 0,
            "alert": 0,
            "watch": 0,
            "total": len(self.active_alerts)
        }
        
        for alert in self.active_alerts.values():
            summary[alert.level.value] += 1
        
        return summary
    
    def cleanup(self, active_swimmer_ids: List[int]):
        """Remove state for swimmers no longer active"""
        # Clean high-risk state
        inactive = [sid for sid in self.high_risk_state.keys() if sid not in active_swimmer_ids]
        for sid in inactive:
            del self.high_risk_state[sid]
        
        # Auto-resolve alerts for swimmers no longer present (they exited water)
        for alert_id, alert in list(self.active_alerts.items()):
            if alert.swimmer_id not in active_swimmer_ids:
                self.resolve_alert(alert_id, time.time())
