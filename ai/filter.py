"""
Detection Filters
=================
Filters to improve accuracy by removing false positives.
Only keeps detections that are likely to be swimmers in water.
"""

import cv2
import numpy as np
from typing import List, Tuple


def filter_by_size(detections: List[Tuple[int, int, int, int, float]], 
                   frame_shape: Tuple[int, int],
                   min_size_ratio: float = 0.005,  # Much more lenient - 0.5% of frame
                   max_size_ratio: float = 0.6) -> List[Tuple[int, int, int, int, float]]:
    """
    Filter detections by bounding box size.
    Removes very small or very large detections (likely false positives).
    
    Args:
        detections: List of (x1, y1, x2, y2, conf)
        frame_shape: (height, width) of frame
        min_size_ratio: Minimum box area as ratio of frame area
        max_size_ratio: Maximum box area as ratio of frame area
    
    Returns:
        Filtered detections
    """
    if not detections:
        return []
    
    frame_area = frame_shape[0] * frame_shape[1]
    filtered = []
    
    for x1, y1, x2, y2, conf in detections:
        box_area = (x2 - x1) * (y2 - y1)
        area_ratio = box_area / frame_area
        
        if min_size_ratio <= area_ratio <= max_size_ratio:
            filtered.append((x1, y1, x2, y2, conf))
    
    return filtered


def filter_by_position(detections: List[Tuple[int, int, int, int, float]],
                      frame_shape: Tuple[int, int],
                      water_zone_ratio: float = 0.8) -> List[Tuple[int, int, int, int, float]]:
    """
    Filter detections by position - swimmers are usually in lower part of frame (water).
    Removes detections in upper part (likely land/sky).
    
    Args:
        detections: List of (x1, y1, x2, y2, conf)
        frame_shape: (height, width) of frame
        water_zone_ratio: Fraction of frame height that is considered "water zone" (from bottom)
    
    Returns:
        Filtered detections
    """
    if not detections:
        return []
    
    frame_height = frame_shape[0]
    water_zone_top = int(frame_height * (1 - water_zone_ratio))
    filtered = []
    
    for x1, y1, x2, y2, conf in detections:
        # Check if detection center is in water zone (lower part of frame)
        center_y = (y1 + y2) // 2
        if center_y >= water_zone_top:
            filtered.append((x1, y1, x2, y2, conf))
    
    return filtered


def detect_water_region(frame: np.ndarray, 
                        lower_half_only: bool = True) -> Tuple[bool, float]:
    """
    Simple water detection using color analysis.
    Looks for blue/cyan colors in the lower half of the frame.
    
    Args:
        frame: BGR image
        lower_half_only: Only check lower half of frame
    
    Returns:
        (has_water, water_confidence) tuple
    """
    h, w = frame.shape[:2]
    
    if lower_half_only:
        # Only check lower half (where water usually is)
        roi = frame[h//2:, :]
    else:
        roi = frame
    
    # Convert to HSV for better color detection
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    
    # Define blue/cyan color range (water colors) - expanded range
    # Lower bound: darker blue
    lower_blue = np.array([90, 30, 30])  # More lenient
    # Upper bound: lighter blue/cyan
    upper_blue = np.array([140, 255, 255])  # Expanded range
    
    # Also check for light blue/white (foam, shallow water)
    lower_light = np.array([0, 0, 200])  # Very light colors
    upper_light = np.array([180, 30, 255])
    
    # Create mask for blue regions
    blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
    light_mask = cv2.inRange(hsv, lower_light, upper_light)
    combined_mask = cv2.bitwise_or(blue_mask, light_mask)
    
    # Calculate percentage of blue/light pixels
    blue_ratio = np.sum(combined_mask > 0) / (combined_mask.shape[0] * combined_mask.shape[1])
    
    # Consider it water if > 5% of lower frame is blue/light (more lenient)
    has_water = blue_ratio > 0.05
    
    return has_water, blue_ratio


def filter_by_water_context(detections: List[Tuple[int, int, int, int, float]],
                            frame: np.ndarray) -> List[Tuple[int, int, int, int, float]]:
    """
    Filter detections based on water presence in frame.
    If no water detected, reject all detections (likely false positives).
    
    Args:
        detections: List of (x1, y1, x2, y2, conf)
        frame: BGR image
    
    Returns:
        Filtered detections (empty if no water detected)
    """
    has_water, water_confidence = detect_water_region(frame)
    
    if not has_water:
        # No water detected - likely false positives
        return []
    
    return detections


def filter_by_motion(detections: List[Tuple[int, int, int, int, float]],
                    prev_detections: List[Tuple[int, int, int, int, float]],
                    motion_threshold: float = 0.1) -> List[Tuple[int, int, int, int, float]]:
    """
    Filter detections by motion - swimmers should move.
    Compares with previous frame detections.
    
    Args:
        detections: Current frame detections
        prev_detections: Previous frame detections
        motion_threshold: Minimum movement ratio to consider valid
    
    Returns:
        Filtered detections
    """
    if not prev_detections:
        # First frame - accept all
        return detections
    
    if not detections:
        return []
    
    # Calculate centers of current detections
    current_centers = [((x1 + x2) // 2, (y1 + y2) // 2) for x1, y1, x2, y2, _ in detections]
    prev_centers = [((x1 + x2) // 2, (y1 + y2) // 2) for x1, y1, x2, y2, _ in prev_detections]
    
    # Simple motion check: if detection is too close to previous, might be static
    # For now, accept all (can be improved with tracking)
    return detections


def apply_all_filters(detections: List[Tuple[int, int, int, int, float]],
                     frame: np.ndarray,
                     frame_shape: Tuple[int, int],
                     strict_mode: bool = False) -> List[Tuple[int, int, int, int, float]]:
    """
    Apply all filters to improve detection accuracy.
    
    Args:
        detections: Raw detections from YOLO
        frame: BGR image
        frame_shape: (height, width)
        strict_mode: If True, requires water detection (rejects all if no water)
                     If False, only filters by size and position (more lenient)
    
    Returns:
        Filtered detections
    """
    if not detections:
        return []
    
    # Step 1: Filter by size (remove tiny/huge boxes) - Very lenient
    filtered = filter_by_size(detections, frame_shape, 
                             min_size_ratio=0.005,  # At least 0.5% of frame (very lenient)
                             max_size_ratio=0.6)    # At most 60% of frame
    
    # Step 2: Filter by position (only lower part = water zone) - More lenient
    filtered = filter_by_position(filtered, frame_shape, water_zone_ratio=0.8)  # 80% from bottom
    
    # Step 3: Water context check (only in strict mode)
    if strict_mode:
        filtered = filter_by_water_context(filtered, frame)
    
    return filtered

