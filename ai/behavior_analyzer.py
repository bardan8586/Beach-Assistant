"""
Swimmer Behavior Analysis Module
=================================
Analyzes swimmer motion, trajectories, and behavior patterns.

Features:
- Motion analysis (velocity, acceleration)
- Trajectory tracking
- Pattern detection (stationary, erratic, normal)
- Risk behavior detection
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from collections import deque
import time
from enum import Enum


class MovementPattern(Enum):
    """Movement pattern types"""
    NORMAL = "normal"
    STATIONARY = "stationary"
    ERRATIC = "erratic"
    RAPID = "rapid"
    UNKNOWN = "unknown"


@dataclass
class MotionMetrics:
    """Motion metrics for a swimmer"""
    velocity: float  # pixels per second
    velocity_x: float
    velocity_y: float
    acceleration: float  # pixels per second^2
    distance_traveled: float  # total pixels
    time_in_view: float  # seconds
    pattern: MovementPattern


@dataclass
class TrajectoryPoint:
    """Single point in a trajectory"""
    x: int
    y: int
    timestamp: float
    frame_idx: int


class BehaviorAnalyzer:
    """
    Analyzes swimmer behavior and motion patterns.
    """
    
    def __init__(
        self,
        max_trajectory_length: int = 100,
        stationary_threshold: float = 5.0,  # pixels per second
        rapid_threshold: float = 50.0,  # pixels per second
        stationary_time_threshold: float = 30.0,  # seconds
        erratic_variance_threshold: float = 1000.0,  # variance in velocity
    ):
        """
        Initialize behavior analyzer.
        
        Args:
            max_trajectory_length: Maximum points to keep in trajectory history
            stationary_threshold: Velocity below this = stationary (pixels/sec)
            rapid_threshold: Velocity above this = rapid movement (pixels/sec)
            stationary_time_threshold: Time stationary before flagging (seconds)
            erratic_variance_threshold: Velocity variance threshold for erratic movement
        """
        self.max_trajectory_length = max_trajectory_length
        self.stationary_threshold = stationary_threshold
        self.rapid_threshold = rapid_threshold
        self.stationary_time_threshold = stationary_time_threshold
        self.erratic_variance_threshold = erratic_variance_threshold
        
        # Track trajectories: track_id -> deque of TrajectoryPoint
        self.trajectories: Dict[int, deque] = {}
        
        # Track motion history: track_id -> deque of (velocity, timestamp)
        self.motion_history: Dict[int, deque] = {}
        
        # Track first seen time: track_id -> timestamp
        self.first_seen: Dict[int, float] = {}
        
        # Track last position: track_id -> (x, y)
        self.last_position: Dict[int, Tuple[int, int]] = {}
        
        # Store current motion metrics: track_id -> MotionMetrics
        self.current_metrics: Dict[int, MotionMetrics] = {}
    
    def update(self, track_id: int, bbox: Tuple[int, int, int, int], 
               timestamp: float, frame_idx: int) -> MotionMetrics:
        """
        Update trajectory and calculate motion metrics for a track.
        
        Args:
            track_id: Unique track ID
            bbox: (x1, y1, x2, y2) bounding box
            timestamp: Current timestamp
            frame_idx: Current frame index
            
        Returns:
            MotionMetrics object
        """
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        
        # Initialize if new track
        if track_id not in self.trajectories:
            self.trajectories[track_id] = deque(maxlen=self.max_trajectory_length)
            self.motion_history[track_id] = deque(maxlen=30)  # Last 30 velocity measurements
            self.first_seen[track_id] = timestamp
        
        # Add current point to trajectory
        point = TrajectoryPoint(center_x, center_y, timestamp, frame_idx)
        self.trajectories[track_id].append(point)
        
        # Calculate velocity
        velocity = 0.0
        velocity_x = 0.0
        velocity_y = 0.0
        acceleration = 0.0
        
        if len(self.trajectories[track_id]) > 1:
            # Get last two points
            prev_point = self.trajectories[track_id][-2]
            curr_point = self.trajectories[track_id][-1]
            
            # Time delta
            dt = curr_point.timestamp - prev_point.timestamp
            if dt > 0:
                # Calculate velocity (pixels per second)
                dx = curr_point.x - prev_point.x
                dy = curr_point.y - prev_point.y
                distance = np.sqrt(dx**2 + dy**2)
                velocity = distance / dt
                velocity_x = dx / dt
                velocity_y = dy / dt
                
                # Store velocity in history
                self.motion_history[track_id].append((velocity, timestamp))
                
                # Calculate acceleration (if we have velocity history)
                if len(self.motion_history[track_id]) > 1:
                    prev_vel, prev_ts = self.motion_history[track_id][-2]
                    curr_vel, curr_ts = self.motion_history[track_id][-1]
                    dt_accel = curr_ts - prev_ts
                    if dt_accel > 0:
                        acceleration = abs(curr_vel - prev_vel) / dt_accel
        
        # Calculate total distance traveled
        distance_traveled = 0.0
        trajectory = list(self.trajectories[track_id])
        for i in range(1, len(trajectory)):
            p1 = trajectory[i-1]
            p2 = trajectory[i]
            distance_traveled += np.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2)
        
        # Time in view
        time_in_view = timestamp - self.first_seen[track_id]
        
        # Determine movement pattern
        pattern = self._classify_pattern(track_id, velocity, time_in_view)
        
        # Update last position
        self.last_position[track_id] = (center_x, center_y)
        
        metrics = MotionMetrics(
            velocity=velocity,
            velocity_x=velocity_x,
            velocity_y=velocity_y,
            acceleration=acceleration,
            distance_traveled=distance_traveled,
            time_in_view=time_in_view,
            pattern=pattern
        )
        
        # Store metrics
        self.current_metrics[track_id] = metrics
        
        return metrics
    
    def _classify_pattern(self, track_id: int, velocity: float, 
                         time_in_view: float) -> MovementPattern:
        """
        Classify movement pattern based on velocity and history.
        
        Args:
            track_id: Track ID
            velocity: Current velocity
            time_in_view: Time swimmer has been in view
            
        Returns:
            MovementPattern enum
        """
        # Check if stationary
        if velocity < self.stationary_threshold:
            # Check if stationary for too long
            if time_in_view > self.stationary_time_threshold:
                # Check recent velocities
                if len(self.motion_history[track_id]) > 5:
                    recent_velocities = [v for v, _ in list(self.motion_history[track_id])[-5:]]
                    avg_velocity = np.mean(recent_velocities)
                    if avg_velocity < self.stationary_threshold:
                        return MovementPattern.STATIONARY
        
        # Check if rapid
        if velocity > self.rapid_threshold:
            return MovementPattern.RAPID
        
        # Check if erratic (high variance in velocity)
        if len(self.motion_history[track_id]) > 10:
            velocities = [v for v, _ in list(self.motion_history[track_id])[-10:]]
            if len(velocities) > 1:
                variance = np.var(velocities)
                if variance > self.erratic_variance_threshold:
                    return MovementPattern.ERRATIC
        
        return MovementPattern.NORMAL
    
    def get_trajectory(self, track_id: int) -> List[TrajectoryPoint]:
        """
        Get trajectory history for a track.
        
        Args:
            track_id: Track ID
            
        Returns:
            List of TrajectoryPoint objects
        """
        if track_id not in self.trajectories:
            return []
        return list(self.trajectories[track_id])
    
    def get_distance_from_shore(self, track_id: int, frame_height: int) -> float:
        """
        Calculate distance from shore (bottom of frame).
        
        Args:
            track_id: Track ID
            frame_height: Height of frame
            
        Returns:
            Distance from bottom (shore) in pixels
        """
        if track_id not in self.trajectories or len(self.trajectories[track_id]) == 0:
            return 0.0
        
        # Get current position (most recent point)
        current_point = self.trajectories[track_id][-1]
        # Distance from bottom = frame_height - y
        distance = frame_height - current_point.y
        return distance
    
    def cleanup(self, active_track_ids: List[int]):
        """
        Remove trajectories for tracks that are no longer active.
        
        Args:
            active_track_ids: List of currently active track IDs
        """
        active_set = set(active_track_ids)
        to_remove = [tid for tid in self.trajectories.keys() if tid not in active_set]
        
        for tid in to_remove:
            self.trajectories.pop(tid, None)
            self.motion_history.pop(tid, None)
            self.first_seen.pop(tid, None)
            self.last_position.pop(tid, None)
            self.current_metrics.pop(tid, None)
    
    def get_motion_metrics(self, track_id: int) -> Optional[MotionMetrics]:
        """
        Get current motion metrics for a track.
        
        Args:
            track_id: Track ID
            
        Returns:
            MotionMetrics or None if not found
        """
        return self.current_metrics.get(track_id)

