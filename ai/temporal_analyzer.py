"""
Temporal Analyzer - Track behavior changes over time
=====================================================

Key capabilities:
1. Fatigue detection - swimming speed declining over minutes
2. Panic progression - state machine from normal → struggling → drowning
3. Time-in-zone analysis - how long in danger zone?
4. Behavioral anomaly detection - sudden changes in patterns

This is the "memory" of the system - understanding not just "what now"
but "how did we get here" and "where is this going?"
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Deque
from dataclasses import dataclass, field
from collections import deque
from enum import Enum
import time


class SwimmerState(Enum):
    """State machine for drowning progression"""
    NORMAL = "normal"                    # Swimming normally
    RESTING = "resting"                  # Floating/treading, controlled
    TIRING = "tiring"                    # Slowing down, fatigue signs
    STRUGGLING = "struggling"             # Brief struggle, still mobile
    CRITICAL_STRUGGLING = "critical"      # Extended struggle, losing control
    DROWNING = "drowning"                # Active/passive drowning behavior
    RESCUED = "rescued"                  # Exited water safely


@dataclass
class StateTransition:
    """Record of state change"""
    from_state: SwimmerState
    to_state: SwimmerState
    timestamp: float
    trigger_reason: str  # Why did state change?


@dataclass
class FatigueMetrics:
    """Metrics for detecting swimmer fatigue"""
    average_speed: float                  # Average speed (pixels/second)
    speed_trend: float                    # Trend: negative = slowing down
    stroke_rate: float                    # Strokes per minute (if detectable)
    time_in_water: float                  # Total time in water (seconds)
    rest_periods: int                     # Number of times stopped to rest
    distance_traveled: float              # Total distance traveled (pixels)
    efficiency: float                     # Distance per unit of movement (0-1)


@dataclass
class TimelineEvent:
    """Significant event in swimmer's timeline"""
    timestamp: float
    event_type: str  # "entered_danger_zone", "started_struggling", "fatigue_detected", etc.
    severity: int    # 1-10
    description: str


class TemporalAnalyzer:
    """
    Analyzes swimmer behavior over time to detect fatigue and panic progression
    """
    
    def __init__(self):
        # State tracking: track_id -> current state
        self.swimmer_states: Dict[int, SwimmerState] = {}
        
        # State history: track_id -> list of transitions
        self.state_history: Dict[int, List[StateTransition]] = {}
        
        # Timeline: track_id -> list of significant events
        self.timeline: Dict[int, List[TimelineEvent]] = {}
        
        # Speed history: track_id -> deque of (timestamp, speed)
        self.speed_history: Dict[int, Deque[Tuple[float, float]]] = {}
        self.max_speed_history = 120  # Keep 2 minutes at 1 sample/second
        
        # Zone history: track_id -> deque of (timestamp, zone)
        self.zone_history: Dict[int, Deque[Tuple[float, str]]] = {}
        
        # First seen: track_id -> timestamp
        self.first_seen: Dict[int, float] = {}
        
        # Distance traveled: track_id -> total distance
        self.distance_traveled: Dict[int, float] = {}
        
        # Last position: track_id -> (x, y)
        self.last_position: Dict[int, Tuple[int, int]] = {}
        
        # Rest periods: track_id -> count
        self.rest_periods: Dict[int, int] = {}
        
        # State duration: track_id -> seconds in current state
        self.state_duration: Dict[int, float] = {}
        
        # State thresholds (tunable)
        self.FATIGUE_SPEED_DROP = 0.3  # 30% speed drop = fatigue
        self.STRUGGLING_DURATION = 10.0  # 10 seconds struggling = critical
        self.CRITICAL_DURATION = 20.0  # 20 seconds critical = drowning
    
    def update(self, 
               track_id: int, 
               position: Tuple[int, int],
               speed: float,
               zone: str,
               pose_action: Optional[str],
               timestamp: float) -> Tuple[SwimmerState, Optional[StateTransition]]:
        """
        Update temporal analysis for a swimmer
        
        Args:
            track_id: Swimmer ID
            position: Current (x, y) position
            speed: Current speed (pixels/second)
            zone: Current water zone ("safe", "caution", "danger")
            pose_action: Pose-based action classification
            timestamp: Current timestamp
            
        Returns:
            (current_state, state_transition_if_changed)
        """
        # Initialize tracking for new swimmer
        if track_id not in self.swimmer_states:
            self.swimmer_states[track_id] = SwimmerState.NORMAL
            self.state_history[track_id] = []
            self.timeline[track_id] = []
            self.speed_history[track_id] = deque(maxlen=self.max_speed_history)
            self.zone_history[track_id] = deque(maxlen=120)
            self.first_seen[track_id] = timestamp
            self.distance_traveled[track_id] = 0.0
            self.rest_periods[track_id] = 0
            self.state_duration[track_id] = 0.0
            self.last_position[track_id] = position
        
        # Update metrics
        self._update_speed_history(track_id, timestamp, speed)
        self._update_zone_history(track_id, timestamp, zone)
        self._update_distance(track_id, position)
        
        # Get current state
        current_state = self.swimmer_states[track_id]
        
        # Determine new state based on all available data
        new_state = self._determine_state(
            track_id, 
            current_state,
            speed, 
            zone, 
            pose_action, 
            timestamp
        )
        
        # Check for state transition
        transition = None
        if new_state != current_state:
            transition = self._transition_state(track_id, current_state, new_state, timestamp)
        
        # Update state duration
        if track_id in self.state_history and len(self.state_history[track_id]) > 0:
            last_transition = self.state_history[track_id][-1]
            self.state_duration[track_id] = timestamp - last_transition.timestamp
        
        return new_state, transition
    
    def _update_speed_history(self, track_id: int, timestamp: float, speed: float):
        """Update speed history with temporal smoothing"""
        self.speed_history[track_id].append((timestamp, speed))
    
    def _update_zone_history(self, track_id: int, timestamp: float, zone: str):
        """Track which zones swimmer has been in"""
        self.zone_history[track_id].append((timestamp, zone))
    
    def _update_distance(self, track_id: int, position: Tuple[int, int]):
        """Update total distance traveled"""
        if track_id in self.last_position:
            last_pos = self.last_position[track_id]
            distance = np.sqrt((position[0] - last_pos[0])**2 + (position[1] - last_pos[1])**2)
            self.distance_traveled[track_id] += distance
        
        self.last_position[track_id] = position
    
    def _determine_state(self,
                        track_id: int,
                        current_state: SwimmerState,
                        speed: float,
                        zone: str,
                        pose_action: Optional[str],
                        timestamp: float) -> SwimmerState:
        """
        Determine swimmer state using all available information
        
        State machine transitions:
        NORMAL → RESTING → NORMAL (ok, just taking a break)
        NORMAL → TIRING → STRUGGLING → CRITICAL → DROWNING (danger!)
        """
        # Get fatigue metrics
        fatigue = self.get_fatigue_metrics(track_id, timestamp)
        
        # Get time in current state
        state_time = self.state_duration.get(track_id, 0.0)
        
        # Priority 1: Pose-based drowning detection (most reliable)
        if pose_action in ["ACTIVE_DROWNING", "PASSIVE_DROWNING"]:
            return SwimmerState.DROWNING
        
        # Priority 2: Sustained struggling (critical)
        if pose_action == "STRUGGLING":
            if state_time > self.CRITICAL_DURATION:
                return SwimmerState.CRITICAL_STRUGGLING
            elif state_time > self.STRUGGLING_DURATION:
                return SwimmerState.STRUGGLING
            else:
                # Brief struggle might just be tiring
                return SwimmerState.TIRING
        
        # Priority 3: Fatigue detection
        if fatigue and fatigue.speed_trend < -self.FATIGUE_SPEED_DROP:
            # Speed dropping significantly
            if current_state in [SwimmerState.TIRING, SwimmerState.STRUGGLING]:
                # Already tiring and getting worse
                return SwimmerState.STRUGGLING
            else:
                return SwimmerState.TIRING
        
        # Priority 4: Time-based risk (long time in water)
        if fatigue and fatigue.time_in_water > 600:  # 10 minutes
            # Been in water a long time, check for signs of fatigue
            if fatigue.average_speed < 20:  # Very slow
                return SwimmerState.TIRING
        
        # Priority 5: Resting/floating
        if pose_action in ["FLOATING", "TREADING_WATER"] and speed < 5:
            # Stationary but controlled
            return SwimmerState.RESTING
        
        # Default: Normal swimming
        if speed > 10 and pose_action in ["SWIMMING_NORMAL", None]:
            return SwimmerState.NORMAL
        
        # Maintain current state if no clear change
        return current_state
    
    def _transition_state(self,
                         track_id: int,
                         from_state: SwimmerState,
                         to_state: SwimmerState,
                         timestamp: float) -> StateTransition:
        """Record state transition"""
        # Determine trigger reason
        reason = self._determine_transition_reason(track_id, from_state, to_state)
        
        transition = StateTransition(
            from_state=from_state,
            to_state=to_state,
            timestamp=timestamp,
            trigger_reason=reason
        )
        
        self.state_history[track_id].append(transition)
        self.swimmer_states[track_id] = to_state
        
        # Add to timeline if significant
        severity = self._calculate_transition_severity(from_state, to_state)
        if severity >= 5:
            event = TimelineEvent(
                timestamp=timestamp,
                event_type=f"state_change_{from_state.value}_to_{to_state.value}",
                severity=severity,
                description=f"Swimmer transitioned from {from_state.value} to {to_state.value}: {reason}"
            )
            self.timeline[track_id].append(event)
        
        return transition
    
    def _determine_transition_reason(self,
                                     track_id: int,
                                     from_state: SwimmerState,
                                     to_state: SwimmerState) -> str:
        """Explain why state changed"""
        fatigue = self.get_fatigue_metrics(track_id, time.time())
        
        if to_state == SwimmerState.DROWNING:
            return "Drowning behavior detected by pose analysis"
        elif to_state == SwimmerState.CRITICAL_STRUGGLING:
            return f"Struggling for {self.state_duration.get(track_id, 0):.1f}s"
        elif to_state == SwimmerState.STRUGGLING:
            return "Erratic movement detected"
        elif to_state == SwimmerState.TIRING:
            if fatigue:
                return f"Speed dropped {abs(fatigue.speed_trend)*100:.0f}%"
            return "Signs of fatigue"
        elif to_state == SwimmerState.RESTING:
            return "Stationary but controlled"
        elif to_state == SwimmerState.NORMAL:
            return "Resumed normal swimming"
        
        return "State change"
    
    def _calculate_transition_severity(self, from_state: SwimmerState, to_state: SwimmerState) -> int:
        """Calculate severity of state transition (1-10)"""
        severity_map = {
            SwimmerState.NORMAL: 1,
            SwimmerState.RESTING: 2,
            SwimmerState.TIRING: 4,
            SwimmerState.STRUGGLING: 7,
            SwimmerState.CRITICAL_STRUGGLING: 9,
            SwimmerState.DROWNING: 10,
        }
        
        from_severity = severity_map.get(from_state, 1)
        to_severity = severity_map.get(to_state, 1)
        
        # Severity is based on destination state and how far we moved
        return min(10, to_severity + abs(to_severity - from_severity))
    
    def get_fatigue_metrics(self, track_id: int, current_time: float) -> Optional[FatigueMetrics]:
        """
        Calculate comprehensive fatigue metrics
        """
        if track_id not in self.speed_history or len(self.speed_history[track_id]) < 10:
            return None
        
        speed_data = list(self.speed_history[track_id])
        
        # Calculate average speed
        speeds = [s for _, s in speed_data]
        avg_speed = np.mean(speeds)
        
        # Calculate speed trend (linear regression)
        if len(speed_data) >= 20:
            recent_speeds = speeds[-20:]  # Last 20 samples
            older_speeds = speeds[-40:-20] if len(speeds) >= 40 else speeds[:20]
            
            recent_avg = np.mean(recent_speeds)
            older_avg = np.mean(older_speeds)
            
            # Trend as percentage change
            speed_trend = (recent_avg - older_avg) / (older_avg + 1e-6)
        else:
            speed_trend = 0.0
        
        # Calculate time in water
        time_in_water = current_time - self.first_seen.get(track_id, current_time)
        
        # Calculate efficiency (distance per movement)
        total_distance = self.distance_traveled.get(track_id, 0.0)
        if time_in_water > 0:
            efficiency = min(1.0, total_distance / (avg_speed * time_in_water + 1e-6))
        else:
            efficiency = 1.0
        
        return FatigueMetrics(
            average_speed=avg_speed,
            speed_trend=speed_trend,
            stroke_rate=0.0,  # TODO: Calculate from pose if available
            time_in_water=time_in_water,
            rest_periods=self.rest_periods.get(track_id, 0),
            distance_traveled=total_distance,
            efficiency=efficiency
        )
    
    def get_time_in_zone(self, track_id: int, zone: str, current_time: float) -> float:
        """
        Calculate how long swimmer has been in a specific zone
        
        Args:
            track_id: Swimmer ID
            zone: Zone name ("safe", "caution", "danger")
            current_time: Current timestamp
            
        Returns:
            Time in seconds
        """
        if track_id not in self.zone_history:
            return 0.0
        
        zone_data = list(self.zone_history[track_id])
        
        # Find continuous time in current zone
        time_in_zone = 0.0
        for i in range(len(zone_data) - 1, -1, -1):
            timestamp, z = zone_data[i]
            if z == zone:
                time_in_zone = current_time - timestamp
            else:
                break
        
        return time_in_zone
    
    def get_panic_progression_score(self, track_id: int) -> float:
        """
        Calculate panic progression score (0-100)
        
        Higher score = more advanced in drowning progression
        """
        if track_id not in self.swimmer_states:
            return 0.0
        
        state = self.swimmer_states[track_id]
        duration = self.state_duration.get(track_id, 0.0)
        
        # Base score from state
        state_scores = {
            SwimmerState.NORMAL: 0,
            SwimmerState.RESTING: 10,
            SwimmerState.TIRING: 30,
            SwimmerState.STRUGGLING: 60,
            SwimmerState.CRITICAL_STRUGGLING: 85,
            SwimmerState.DROWNING: 100,
        }
        
        base_score = state_scores.get(state, 0)
        
        # Add time-in-state bonus (longer in bad state = worse)
        if state in [SwimmerState.TIRING, SwimmerState.STRUGGLING, SwimmerState.CRITICAL_STRUGGLING]:
            time_bonus = min(20, duration / 2)  # +1 point per 2 seconds, max 20
            base_score += time_bonus
        
        return min(100, base_score)
    
    def get_state_history_summary(self, track_id: int) -> str:
        """
        Get human-readable summary of state history
        """
        if track_id not in self.state_history or len(self.state_history[track_id]) == 0:
            return "No history"
        
        transitions = self.state_history[track_id]
        summary_parts = []
        
        for trans in transitions[-5:]:  # Last 5 transitions
            duration = trans.timestamp - self.first_seen.get(track_id, trans.timestamp)
            summary_parts.append(f"{trans.to_state.value} ({duration:.0f}s)")
        
        return " → ".join(summary_parts)
    
    def cleanup(self, active_track_ids: List[int]):
        """Remove data for inactive tracks"""
        all_ids = list(self.swimmer_states.keys())
        for track_id in all_ids:
            if track_id not in active_track_ids:
                self.swimmer_states.pop(track_id, None)
                self.state_history.pop(track_id, None)
                self.timeline.pop(track_id, None)
                self.speed_history.pop(track_id, None)
                self.zone_history.pop(track_id, None)
                self.first_seen.pop(track_id, None)
                self.distance_traveled.pop(track_id, None)
                self.last_position.pop(track_id, None)
                self.rest_periods.pop(track_id, None)
                self.state_duration.pop(track_id, None)
