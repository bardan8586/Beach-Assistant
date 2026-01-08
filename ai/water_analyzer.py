"""
Water Analysis Module
====================
Analyzes water regions, zones, and conditions in beach video frames.

Features:
- Water detection (color + texture analysis)
- Zone mapping (safe/danger zones)
- Water conditions (calm/rough, visibility)
- Zone violation detection
"""

import cv2
import numpy as np
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class WaterZone(Enum):
    """Water zone types"""
    SAFE = "safe"          # Shallow, near shore
    CAUTION = "caution"    # Medium depth
    DANGER = "danger"      # Deep, far from shore


@dataclass
class WaterRegion:
    """Represents a water region in the frame"""
    zone: WaterZone
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    confidence: float
    center: Tuple[int, int]


@dataclass
class WaterConditions:
    """Water conditions analysis"""
    has_water: bool
    water_confidence: float
    visibility_estimate: float  # 0-1, higher = clearer
    wave_activity: float  # 0-1, higher = more waves
    calm_score: float  # 0-1, higher = calmer


class WaterAnalyzer:
    """
    Analyzes water in beach video frames.
    """
    
    def __init__(
        self,
        frame_shape: Tuple[int, int],
        safe_zone_ratio: float = 0.3,  # Bottom 30% = safe (shallow)
        caution_zone_ratio: float = 0.5,  # Next 50% = caution
        danger_zone_ratio: float = 0.2,  # Top 20% = danger (deep)
        shore_line_y: Optional[int] = None,  # Actual shore line Y coordinate
    ):
        """
        Initialize water analyzer.
        
        Args:
            frame_shape: (height, width) of video frames
            safe_zone_ratio: Fraction of frame height for safe zone (from bottom)
            caution_zone_ratio: Fraction for caution zone (middle)
            danger_zone_ratio: Fraction for danger zone (top)
            shore_line_y: Actual shore line Y coordinate (if None, uses frame bottom)
        """
        self.frame_h, self.frame_w = frame_shape[:2]
        self.shore_line_y = shore_line_y
        self.safe_zone_ratio = safe_zone_ratio
        self.caution_zone_ratio = caution_zone_ratio
        self.danger_zone_ratio = danger_zone_ratio
        
        # Update zone boundaries based on actual shore line
        self._update_zones()
    
    def _update_zones(self):
        """Update zone boundaries based on shore line or frame bottom."""
        if self.shore_line_y is not None:
            # Use actual shore line as reference
            # Safe zone: from shore line down (beach area)
            # Water zones: from shore line up
            water_area_height = self.shore_line_y
            safe_zone_height = self.frame_h - self.shore_line_y
            
            # Safe zone is on beach (below shore)
            self.safe_zone_top = self.shore_line_y
            # Caution zone: first part of water (near shore)
            self.caution_zone_top = int(self.shore_line_y - water_area_height * self.caution_zone_ratio)
            # Danger zone: deep water (top)
            self.danger_zone_top = 0
        else:
            # Fallback: use frame bottom as reference
            self.safe_zone_top = int(self.frame_h * (1 - self.safe_zone_ratio))
            self.caution_zone_top = int(self.frame_h * (1 - self.safe_zone_ratio - self.caution_zone_ratio))
            self.danger_zone_top = 0
        
        # Zone regions
        self.safe_zone = (0, self.safe_zone_top, self.frame_w, self.frame_h)
        self.caution_zone = (0, self.caution_zone_top, self.frame_w, self.safe_zone_top)
        self.danger_zone = (0, 0, self.frame_w, self.caution_zone_top)
    
    def update_shore_line(self, shore_line_y: int):
        """Update shore line and recalculate zones."""
        self.shore_line_y = shore_line_y
        self._update_zones()
    
    def detect_water(self, frame: np.ndarray) -> Tuple[bool, float]:
        """
        Detect if water is present in frame using color and texture analysis.
        
        Args:
            frame: BGR image
            
        Returns:
            (has_water, confidence) tuple
        """
        h, w = frame.shape[:2]
        
        # Focus on lower 70% of frame (where water usually is)
        roi = frame[int(h * 0.3):, :]
        
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        # Define water color ranges
        # Blue/cyan range
        lower_blue = np.array([90, 30, 30])
        upper_blue = np.array([140, 255, 255])
        
        # Light blue/white (foam, shallow water, reflections)
        lower_light = np.array([0, 0, 200])
        upper_light = np.array([180, 30, 255])
        
        # Teal/turquoise (tropical water)
        lower_teal = np.array([80, 50, 50])
        upper_teal = np.array([100, 255, 255])
        
        # Create masks
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
        light_mask = cv2.inRange(hsv, lower_light, upper_light)
        teal_mask = cv2.inRange(hsv, lower_teal, upper_teal)
        combined_mask = cv2.bitwise_or(cv2.bitwise_or(blue_mask, light_mask), teal_mask)
        
        # Calculate water pixel ratio
        water_ratio = np.sum(combined_mask > 0) / (combined_mask.shape[0] * combined_mask.shape[1])
        
        # Texture analysis for water-like patterns
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        texture_variance = np.var(laplacian)
        
        # Water typically has moderate texture (waves, ripples)
        has_texture = 50 < texture_variance < 5000
        
        # Combine color and texture evidence
        has_water = water_ratio > 0.05 or (water_ratio > 0.02 and has_texture)
        confidence = min(water_ratio * 2, 1.0)
        
        return has_water, confidence
    
    def analyze_conditions(self, frame: np.ndarray) -> WaterConditions:
        """
        Analyze water conditions (visibility, wave activity, calmness).
        
        Args:
            frame: BGR image
            
        Returns:
            WaterConditions object
        """
        has_water, water_conf = self.detect_water(frame)
        
        if not has_water:
            return WaterConditions(
                has_water=False,
                water_confidence=0.0,
                visibility_estimate=0.0,
                wave_activity=0.0,
                calm_score=1.0
            )
        
        h, w = frame.shape[:2]
        roi = frame[int(h * 0.3):, :]  # Lower 70%
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # Visibility estimate: based on contrast and clarity
        # Higher contrast = better visibility
        contrast = np.std(gray)
        visibility = min(contrast / 50.0, 1.0)  # Normalize
        
        # Wave activity: based on edge density and texture variance
        # More edges = more waves/ripples
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
        
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        texture_var = np.var(laplacian)
        
        # Combine edge density and texture for wave activity
        wave_activity = min((edge_density * 5 + texture_var / 1000), 1.0)
        
        # Calm score: inverse of wave activity (with some smoothing)
        calm_score = max(1.0 - wave_activity, 0.3)  # Never completely calm
        
        return WaterConditions(
            has_water=True,
            water_confidence=water_conf,
            visibility_estimate=visibility,
            wave_activity=wave_activity,
            calm_score=calm_score
        )
    
    def get_zone_for_position(self, x: int, y: int) -> WaterZone:
        """
        Determine which zone a position (x, y) belongs to.
        
        Args:
            x: X coordinate
            y: Y coordinate (0 = top, frame_h = bottom)
            
        Returns:
            WaterZone enum
        """
        if y >= self.safe_zone_top:
            return WaterZone.SAFE
        elif y >= self.caution_zone_top:
            return WaterZone.CAUTION
        else:
            return WaterZone.DANGER
    
    def get_zone_for_bbox(self, bbox: Tuple[int, int, int, int]) -> WaterZone:
        """
        Determine zone for a bounding box (uses center point).
        
        Args:
            bbox: (x1, y1, x2, y2)
            
        Returns:
            WaterZone enum
        """
        x1, y1, x2, y2 = bbox
        center_y = (y1 + y2) // 2
        return self.get_zone_for_position((x1 + x2) // 2, center_y)
    
    def get_zone_regions(self) -> Dict[WaterZone, Tuple[int, int, int, int]]:
        """
        Get bounding boxes for each zone.
        
        Returns:
            Dictionary mapping WaterZone to (x1, y1, x2, y2)
        """
        return {
            WaterZone.SAFE: self.safe_zone,
            WaterZone.CAUTION: self.caution_zone,
            WaterZone.DANGER: self.danger_zone
        }
    
    def draw_zones(self, frame: np.ndarray, alpha: float = 0.3) -> np.ndarray:
        """
        Draw zone overlays on frame.
        
        Args:
            frame: BGR image
            alpha: Transparency of overlay
            
        Returns:
            Frame with zone overlays
        """
        overlay = frame.copy()
        
        # Draw zones with colors
        # Safe = green, Caution = yellow, Danger = red
        zones = self.get_zone_regions()
        colors = {
            WaterZone.SAFE: (0, 255, 0),      # Green
            WaterZone.CAUTION: (0, 255, 255),  # Yellow (BGR)
            WaterZone.DANGER: (0, 0, 255)     # Red
        }
        
        for zone, (x1, y1, x2, y2) in zones.items():
            color = colors[zone]
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)  # Filled
        
        # Blend with original
        result = cv2.addWeighted(frame, 1 - alpha, overlay, alpha, 0)
        
        # Draw zone labels with background for better visibility
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.8
        thickness = 2
        
        # SAFE zone label
        safe_text = "SAFE ZONE"
        (text_w, text_h), _ = cv2.getTextSize(safe_text, font, font_scale, thickness)
        cv2.rectangle(result, (5, self.frame_h - text_h - 10), (text_w + 15, self.frame_h + 5), (0, 255, 0), -1)
        cv2.putText(result, safe_text, (10, self.frame_h - 5), font, font_scale, (0, 0, 0), thickness)
        
        # CAUTION zone label
        caution_text = "CAUTION ZONE"
        (text_w, text_h), _ = cv2.getTextSize(caution_text, font, font_scale, thickness)
        cv2.rectangle(result, (5, self.safe_zone_top - text_h - 5), (text_w + 15, self.safe_zone_top + 5), (0, 255, 255), -1)
        cv2.putText(result, caution_text, (10, self.safe_zone_top), font, font_scale, (0, 0, 0), thickness)
        
        # DANGER zone label
        danger_text = "DANGER ZONE"
        (text_w, text_h), _ = cv2.getTextSize(danger_text, font, font_scale, thickness)
        cv2.rectangle(result, (5, self.caution_zone_top - text_h - 5), (text_w + 15, self.caution_zone_top + 5), (0, 0, 255), -1)
        cv2.putText(result, danger_text, (10, self.caution_zone_top), font, font_scale, (255, 255, 255), thickness)
        
        return result

