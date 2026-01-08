"""
Scene Analyzer
==============
Analyzes the beach scene to understand:
- Shore/beach line (where water meets land)
- Horizon line
- Camera perspective
- Distance estimation
"""

import cv2
import numpy as np
from typing import Tuple, Optional, List
from dataclasses import dataclass


@dataclass
class SceneGeometry:
    """Scene geometry information"""
    shore_line_y: int  # Y coordinate where water meets land
    horizon_y: int  # Y coordinate of horizon
    water_start_y: int  # Y coordinate where water starts (from top)
    beach_start_y: int  # Y coordinate where beach/sand starts
    has_valid_geometry: bool


class SceneAnalyzer:
    """
    Analyzes beach scene to understand geometry and context.
    """
    
    def __init__(self, frame_shape: Tuple[int, int]):
        """
        Initialize scene analyzer.
        
        Args:
            frame_shape: (height, width) of frames
        """
        self.frame_h, self.frame_w = frame_shape
        self.cached_geometry: Optional[SceneGeometry] = None
        self.frame_count = 0
    
    def detect_shore_line(self, frame: np.ndarray) -> Optional[int]:
        """
        Detect the shore line (where water meets beach/sand).
        
        Uses edge detection and color analysis to find the boundary.
        
        Args:
            frame: BGR image
            
        Returns:
            Y coordinate of shore line, or None if not detected
        """
        h, w = frame.shape[:2]
        
        # Focus on lower 80% of frame (where shore usually is)
        roi = frame[int(h * 0.2):, :]
        roi_h = roi.shape[0]
        
        # Convert to HSV for better color separation
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        # Detect water (blue/cyan colors)
        lower_water = np.array([90, 30, 30])
        upper_water = np.array([140, 255, 255])
        water_mask = cv2.inRange(hsv, lower_water, upper_water)
        
        # Detect sand/beach (brown/yellow/tan colors)
        # Sand colors in HSV
        lower_sand1 = np.array([10, 50, 100])  # Light brown/tan
        upper_sand1 = np.array([30, 255, 255])
        lower_sand2 = np.array([0, 0, 150])  # Light/white sand
        upper_sand2 = np.array([180, 50, 255])
        
        sand_mask1 = cv2.inRange(hsv, lower_sand1, upper_sand1)
        sand_mask2 = cv2.inRange(hsv, lower_sand2, upper_sand2)
        sand_mask = cv2.bitwise_or(sand_mask1, sand_mask2)
        
        # Find transition from water to sand
        # Scan from bottom to top, find where sand appears
        shore_y = None
        scan_step = 5  # Check every 5 pixels
        
        for y in range(roi_h - 50, 50, -scan_step):  # From bottom to top
            row_water = np.sum(water_mask[y, :] > 0)
            row_sand = np.sum(sand_mask[y, :] > 0)
            row_total = w
            
            water_ratio = row_water / row_total
            sand_ratio = row_sand / row_total
            
            # Shore line is where we transition from mostly water to mostly sand
            # Or where sand appears significantly
            if sand_ratio > 0.15 and water_ratio < 0.5:
                shore_y = y + int(h * 0.2)  # Adjust for ROI offset
                break
        
        # Alternative: Use edge detection to find horizontal edges (shore line)
        if shore_y is None:
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            
            # Find horizontal lines (shore line is usually horizontal)
            # Use HoughLinesP for horizontal lines
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, 
                                   minLineLength=w//3, maxLineGap=50)
            
            if lines is not None:
                # Find the lowest horizontal line (likely shore)
                horizontal_lines = []
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    # Check if line is roughly horizontal
                    if abs(y2 - y1) < 20:  # Nearly horizontal
                        avg_y = (y1 + y2) // 2
                        horizontal_lines.append(avg_y)
                
                if horizontal_lines:
                    # Use the lowest horizontal line as shore
                    shore_y = max(horizontal_lines) + int(h * 0.2)
        
        return shore_y
    
    def detect_horizon(self, frame: np.ndarray) -> Optional[int]:
        """
        Detect horizon line (sky/water or sky/land boundary).
        
        Args:
            frame: BGR image
            
        Returns:
            Y coordinate of horizon, or None if not detected
        """
        h, w = frame.shape[:2]
        
        # Focus on upper 50% of frame
        roi = frame[:int(h * 0.5), :]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # Detect edges
        edges = cv2.Canny(gray, 50, 150)
        
        # Find horizontal lines in upper portion
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=80,
                               minLineLength=w//4, maxLineGap=30)
        
        if lines is not None:
            horizontal_lines = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                if abs(y2 - y1) < 15:  # Nearly horizontal
                    avg_y = (y1 + y2) // 2
                    horizontal_lines.append(avg_y)
            
            if horizontal_lines:
                # Horizon is usually the highest horizontal line
                horizon_y = min(horizontal_lines)
                return horizon_y
        
        # Fallback: assume horizon is at 1/3 from top
        return int(h * 0.33)
    
    def analyze_scene(self, frame: np.ndarray, use_cache: bool = True) -> SceneGeometry:
        """
        Analyze scene to extract geometry information.
        
        Args:
            frame: BGR image
            use_cache: If True, cache result for a few frames (shore doesn't change much)
            
        Returns:
            SceneGeometry object
        """
        # Use cached geometry for a few frames (shore line is relatively stable)
        if use_cache and self.cached_geometry and self.frame_count < 30:
            self.frame_count += 1
            return self.cached_geometry
        
        # Detect shore line
        shore_y = self.detect_shore_line(frame)
        
        # Detect horizon
        horizon_y = self.detect_horizon(frame)
        
        # If shore not detected, use fallback (bottom 30% of frame)
        if shore_y is None:
            shore_y = int(self.frame_h * 0.7)
        
        # Determine water start (usually near horizon or top)
        water_start_y = horizon_y if horizon_y else int(self.frame_h * 0.1)
        
        # Beach starts at shore line
        beach_start_y = shore_y
        
        geometry = SceneGeometry(
            shore_line_y=shore_y,
            horizon_y=horizon_y if horizon_y else int(self.frame_h * 0.33),
            water_start_y=water_start_y,
            beach_start_y=beach_start_y,
            has_valid_geometry=(shore_y is not None)
        )
        
        # Cache for next frames
        if use_cache:
            self.cached_geometry = geometry
            self.frame_count = 0
        
        return geometry
    
    def estimate_distance(self, bbox: Tuple[int, int, int, int], 
                        scene_geometry: SceneGeometry) -> float:
        """
        Estimate distance of object from shore based on position and size.
        
        Args:
            bbox: (x1, y1, x2, y2) bounding box
            scene_geometry: Scene geometry information
            
        Returns:
            Estimated distance in "units" (normalized 0-1, where 1 = far)
        """
        x1, y1, x2, y2 = bbox
        center_y = (y1 + y2) // 2
        box_height = y2 - y1
        
        # Distance based on position relative to shore
        # Objects above shore are in water (farther from camera)
        if center_y < scene_geometry.shore_line_y:
            # In water - estimate based on how far above shore
            distance_from_shore = scene_geometry.shore_line_y - center_y
            # Normalize by frame height
            normalized_distance = distance_from_shore / self.frame_h
        else:
            # On beach - close to camera
            normalized_distance = 0.1
        
        # Also consider box size - smaller boxes are usually farther
        size_factor = box_height / self.frame_h
        # Smaller size = farther away
        if size_factor < 0.1:
            normalized_distance = max(normalized_distance, 0.7)  # Far
        elif size_factor < 0.15:
            normalized_distance = max(normalized_distance, 0.5)  # Medium
        
        return min(normalized_distance, 1.0)
    
    def draw_scene_geometry(self, frame: np.ndarray, 
                           geometry: SceneGeometry) -> np.ndarray:
        """
        Draw scene geometry on frame for visualization.
        
        Args:
            frame: BGR image
            geometry: Scene geometry to draw
            
        Returns:
            Frame with geometry overlays
        """
        result = frame.copy()
        
        # Draw shore line
        if geometry.has_valid_geometry:
            cv2.line(result, (0, geometry.shore_line_y), 
                    (self.frame_w, geometry.shore_line_y), 
                    (0, 255, 255), 3)  # Yellow line
            cv2.putText(result, "SHORE LINE", (10, geometry.shore_line_y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Draw horizon
        if geometry.horizon_y:
            cv2.line(result, (0, geometry.horizon_y), 
                    (self.frame_w, geometry.horizon_y), 
                    (255, 255, 0), 2)  # Cyan line
            cv2.putText(result, "HORIZON", (10, geometry.horizon_y + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        
        return result

