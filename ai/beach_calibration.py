"""
Beach Calibration Engine - Learn beach-specific patterns
=========================================================

Purpose: Every beach is unique. This module learns:
- Normal swimmer behavior patterns (speed, duration, zones)
- Popular swimming areas (heatmap of activity)
- Entry/exit points
- Peak activity times
- Typical crowd density
- Baseline risk levels

After calibration (1-2 hours), the system understands:
"What's NORMAL for THIS beach?"

This enables:
- Anomaly detection (behavior that's unusual FOR THIS BEACH)
- Adaptive alerting (reduce false alarms)
- Beach-specific risk scoring
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import pickle
import json
from pathlib import Path


@dataclass
class BeachProfile:
    """Statistical profile of beach-specific patterns"""
    beach_id: str
    
    # Swimmer behavior statistics
    avg_swimming_speed: float = 0.0
    std_swimming_speed: float = 0.0
    avg_time_in_water: float = 0.0
    std_time_in_water: float = 0.0
    
    # Spatial patterns
    activity_heatmap: np.ndarray = field(default_factory=lambda: np.zeros((100, 100)))
    popular_zones: List[Tuple[int, int, int, int]] = field(default_factory=list)  # (x1,y1,x2,y2)
    entry_points: List[Tuple[int, int]] = field(default_factory=list)  # (x, y)
    exit_points: List[Tuple[int, int]] = field(default_factory=list)
    
    # Temporal patterns
    peak_hours: List[int] = field(default_factory=list)  # Hours of day (0-23)
    avg_crowd_density: float = 0.0
    
    # Risk baselines
    baseline_risk_distribution: Dict[str, float] = field(default_factory=dict)  # risk_level -> percentage
    
    # Calibration metadata
    calibration_samples: int = 0
    last_calibrated: float = 0.0
    is_calibrated: bool = False


@dataclass
class CalibrationSample:
    """Single observation for calibration"""
    swimmer_id: int
    speed: float
    time_in_water: float
    positions: List[Tuple[int, int]]  # Path taken
    zones_visited: List[str]
    risk_level: str
    entry_point: Optional[Tuple[int, int]]
    exit_point: Optional[Tuple[int, int]]


class BeachCalibration:
    """
    Learns and stores beach-specific behavioral patterns
    """
    
    def __init__(self, beach_id: str = "default", calibration_samples_needed: int = 200):
        """
        Args:
            beach_id: Unique identifier for this beach
            calibration_samples_needed: Minimum samples to consider calibrated
        """
        self.beach_id = beach_id
        self.profile = BeachProfile(beach_id=beach_id)
        self.calibration_samples_needed = calibration_samples_needed
        
        # Temporary storage during calibration
        self.samples: List[CalibrationSample] = []
        
        # Real-time tracking for calibration
        self.swimmer_first_seen: Dict[int, Tuple[float, Tuple[int, int]]] = {}  # id -> (timestamp, position)
        self.swimmer_paths: Dict[int, List[Tuple[int, int]]] = {}
        
    def add_observation(self,
                       swimmer_id: int,
                       position: Tuple[int, int],
                       speed: float,
                       zone: str,
                       risk_level: str,
                       timestamp: float,
                       is_exiting: bool = False):
        """
        Add observation during calibration phase
        
        Args:
            swimmer_id: Swimmer ID
            position: Current (x, y)
            speed: Current speed
            zone: Current zone
            risk_level: Current risk level
            timestamp: Current timestamp
            is_exiting: True if swimmer is leaving water
        """
        # Track first appearance (entry point)
        if swimmer_id not in self.swimmer_first_seen:
            self.swimmer_first_seen[swimmer_id] = (timestamp, position)
            self.swimmer_paths[swimmer_id] = []
        
        # Record path
        if swimmer_id in self.swimmer_paths:
            self.swimmer_paths[swimmer_id].append(position)
        
        # If swimmer is exiting, create calibration sample
        if is_exiting and swimmer_id in self.swimmer_first_seen:
            first_ts, entry_point = self.swimmer_first_seen[swimmer_id]
            time_in_water = timestamp - first_ts
            
            # Calculate average speed from path
            path = self.swimmer_paths.get(swimmer_id, [])
            if len(path) > 1:
                total_distance = sum(
                    np.sqrt((path[i][0] - path[i-1][0])**2 + (path[i][1] - path[i-1][1])**2)
                    for i in range(1, len(path))
                )
                avg_speed = total_distance / (time_in_water + 1e-6)
            else:
                avg_speed = speed
            
            # Create sample
            sample = CalibrationSample(
                swimmer_id=swimmer_id,
                speed=avg_speed,
                time_in_water=time_in_water,
                positions=path,
                zones_visited=[zone],  # Simplified - would track all zones in full version
                risk_level=risk_level,
                entry_point=entry_point,
                exit_point=position
            )
            
            self.samples.append(sample)
            
            # Cleanup
            del self.swimmer_first_seen[swimmer_id]
            del self.swimmer_paths[swimmer_id]
            
            # Check if we have enough samples to calibrate
            if len(self.samples) >= self.calibration_samples_needed and not self.profile.is_calibrated:
                self.compute_profile()
    
    def compute_profile(self):
        """
        Compute beach profile from collected samples
        """
        if len(self.samples) < 10:
            print("⚠️  Not enough samples for calibration")
            return
        
        print(f"\n{'='*60}")
        print(f"🏖️  CALIBRATING BEACH PROFILE: {self.beach_id}")
        print(f"{'='*60}")
        print(f"Samples collected: {len(self.samples)}")
        
        # 1. Compute speed statistics
        speeds = [s.speed for s in self.samples if s.speed > 0]
        if speeds:
            self.profile.avg_swimming_speed = np.mean(speeds)
            self.profile.std_swimming_speed = np.std(speeds)
            print(f"📊 Avg Swimming Speed: {self.profile.avg_swimming_speed:.1f} ± {self.profile.std_swimming_speed:.1f} px/s")
        
        # 2. Compute time-in-water statistics
        times = [s.time_in_water for s in self.samples if s.time_in_water > 0]
        if times:
            self.profile.avg_time_in_water = np.mean(times)
            self.profile.std_time_in_water = np.std(times)
            print(f"⏱️  Avg Time in Water: {self.profile.avg_time_in_water:.1f} ± {self.profile.std_time_in_water:.1f} seconds")
        
        # 3. Build activity heatmap
        self.profile.activity_heatmap = self._build_activity_heatmap()
        print(f"🗺️  Activity heatmap computed (100x100 grid)")
        
        # 4. Identify entry/exit points (clustering)
        entry_points = [s.entry_point for s in self.samples if s.entry_point]
        exit_points = [s.exit_point for s in self.samples if s.exit_point]
        
        if entry_points:
            self.profile.entry_points = self._cluster_points(entry_points, max_clusters=5)
            print(f"🚪 Entry Points: {len(self.profile.entry_points)} identified")
        
        if exit_points:
            self.profile.exit_points = self._cluster_points(exit_points, max_clusters=5)
            print(f"🚪 Exit Points: {len(self.profile.exit_points)} identified")
        
        # 5. Compute risk distribution
        risk_counts = defaultdict(int)
        for s in self.samples:
            risk_counts[s.risk_level] += 1
        
        total = sum(risk_counts.values())
        self.profile.baseline_risk_distribution = {
            risk: count / total for risk, count in risk_counts.items()
        }
        print(f"⚠️  Risk Distribution:")
        for risk, pct in self.profile.baseline_risk_distribution.items():
            print(f"    {risk}: {pct*100:.1f}%")
        
        # 6. Mark as calibrated
        self.profile.is_calibrated = True
        self.profile.calibration_samples = len(self.samples)
        self.profile.last_calibrated = __import__('time').time()
        
        print(f"{'='*60}")
        print(f"✅ CALIBRATION COMPLETE!")
        print(f"{'='*60}\n")
    
    def _build_activity_heatmap(self, grid_size: int = 100) -> np.ndarray:
        """
        Build heatmap of where swimmers spend time
        """
        heatmap = np.zeros((grid_size, grid_size))
        
        # Find bounds of all positions
        all_positions = []
        for sample in self.samples:
            all_positions.extend(sample.positions)
        
        if not all_positions:
            return heatmap
        
        positions_array = np.array(all_positions)
        min_x, min_y = positions_array.min(axis=0)
        max_x, max_y = positions_array.max(axis=0)
        
        # Map positions to grid
        for sample in self.samples:
            for x, y in sample.positions:
                # Normalize to 0-1
                norm_x = (x - min_x) / (max_x - min_x + 1e-6)
                norm_y = (y - min_y) / (max_y - min_y + 1e-6)
                
                # Map to grid
                grid_x = int(norm_x * (grid_size - 1))
                grid_y = int(norm_y * (grid_size - 1))
                
                heatmap[grid_y, grid_x] += 1
        
        # Normalize
        if heatmap.max() > 0:
            heatmap = heatmap / heatmap.max()
        
        return heatmap
    
    def _cluster_points(self, points: List[Tuple[int, int]], max_clusters: int = 5) -> List[Tuple[int, int]]:
        """
        Simple clustering to find common entry/exit points
        Uses simple distance-based clustering
        """
        if not points or len(points) < 3:
            return points
        
        points_array = np.array(points)
        clusters = []
        used = set()
        
        # Simple greedy clustering: find densest points
        for _ in range(max_clusters):
            if len(used) >= len(points):
                break
            
            # Find point with most neighbors (not yet used)
            best_center = None
            best_density = 0
            
            for i, p in enumerate(points_array):
                if i in used:
                    continue
                
                # Count neighbors within radius
                distances = np.linalg.norm(points_array - p, axis=1)
                neighbors = np.sum(distances < 100)  # Within 100 pixels
                
                if neighbors > best_density:
                    best_density = neighbors
                    best_center = p
            
            if best_center is not None:
                clusters.append(tuple(best_center.astype(int)))
                
                # Mark nearby points as used
                distances = np.linalg.norm(points_array - best_center, axis=1)
                nearby = np.where(distances < 100)[0]
                used.update(nearby)
        
        return clusters if clusters else [(int(p[0]), int(p[1])) for p in points_array[:max_clusters]]
    
    def is_anomalous_speed(self, speed: float, threshold_sigmas: float = 2.0) -> bool:
        """
        Check if speed is anomalous for this beach
        
        Args:
            speed: Speed to check
            threshold_sigmas: How many standard deviations = anomalous
            
        Returns:
            True if anomalous
        """
        if not self.profile.is_calibrated:
            return False  # Can't determine without calibration
        
        if self.profile.std_swimming_speed == 0:
            return False
        
        z_score = abs(speed - self.profile.avg_swimming_speed) / self.profile.std_swimming_speed
        return z_score > threshold_sigmas
    
    def is_anomalous_duration(self, duration: float, threshold_sigmas: float = 2.0) -> bool:
        """
        Check if time-in-water is anomalous for this beach
        """
        if not self.profile.is_calibrated:
            return False
        
        if self.profile.std_time_in_water == 0:
            return False
        
        z_score = abs(duration - self.profile.avg_time_in_water) / self.profile.std_time_in_water
        return z_score > threshold_sigmas
    
    def get_activity_level(self, position: Tuple[int, int], frame_shape: Tuple[int, int]) -> float:
        """
        Get activity level at a position (0-1)
        
        Args:
            position: (x, y) position
            frame_shape: (height, width) of frame
            
        Returns:
            Activity level 0-1 (1 = very popular spot)
        """
        if not self.profile.is_calibrated:
            return 0.5  # Unknown
        
        # Map position to heatmap grid
        x, y = position
        h, w = frame_shape
        
        grid_x = int((x / w) * (self.profile.activity_heatmap.shape[1] - 1))
        grid_y = int((y / h) * (self.profile.activity_heatmap.shape[0] - 1))
        
        grid_x = np.clip(grid_x, 0, self.profile.activity_heatmap.shape[1] - 1)
        grid_y = np.clip(grid_y, 0, self.profile.activity_heatmap.shape[0] - 1)
        
        return self.profile.activity_heatmap[grid_y, grid_x]
    
    def save_profile(self, filepath: str):
        """Save calibrated profile to disk"""
        with open(filepath, 'wb') as f:
            pickle.dump(self.profile, f)
        print(f"💾 Beach profile saved to {filepath}")
    
    def load_profile(self, filepath: str) -> bool:
        """Load calibrated profile from disk"""
        try:
            with open(filepath, 'rb') as f:
                self.profile = pickle.load(f)
            print(f"📁 Beach profile loaded from {filepath}")
            return True
        except:
            print(f"⚠️  Could not load profile from {filepath}")
            return False
    
    def get_calibration_progress(self) -> Tuple[int, int, float]:
        """
        Get calibration progress
        
        Returns:
            (current_samples, needed_samples, progress_percent)
        """
        progress = (len(self.samples) / self.calibration_samples_needed) * 100
        return len(self.samples), self.calibration_samples_needed, min(100, progress)
