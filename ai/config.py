"""
Configuration file for Beach Safety AI Pipeline.

Set these via environment variables or modify defaults here.
"""

import os
from pathlib import Path

# ===== Detection Configuration =====
# Detector type: "yolo" (local YOLOv8) or "roboflow" (Roboflow Inference API)
DETECTOR_TYPE = os.getenv("DETECTOR_TYPE", "yolo")

# YOLOv8 model selection (only used if DETECTOR_TYPE="yolo")
# Options: yolov8n.pt (nano, fastest), yolov8s.pt (small, balanced), 
#          yolov8m.pt (medium, better accuracy), yolov8l.pt (large), yolov8x.pt (xlarge, best)
MODEL_NAME = os.getenv("MODEL_NAME", "yolov8s.pt")  # Default: small for better accuracy

# Detection confidence threshold (0.0 to 1.0)
# Higher = fewer false positives but might miss some swimmers
CONF_THRESHOLD = float(os.getenv("CONF_THRESHOLD", "0.5"))

# IOU threshold for non-maximum suppression
IOU_THRESHOLD = float(os.getenv("IOU_THRESHOLD", "0.5"))

# ===== Roboflow Configuration (only used if DETECTOR_TYPE="roboflow") =====
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY", "")
ROBOFLOW_MODEL_ID = os.getenv("ROBOFLOW_MODEL_ID", "")  # e.g., "swimmer-detection/1"
ROBOFLOW_VERSION = int(os.getenv("ROBOFLOW_VERSION", "1"))

# ===== Filter Configuration =====
# Filter strictness: False = lenient (only size/position), True = strict (requires water detection)
FILTER_STRICT_MODE = os.getenv("FILTER_STRICT_MODE", "false").lower() == "true"

# Size filter: minimum and maximum bounding box size as ratio of frame
MIN_SIZE_RATIO = float(os.getenv("MIN_SIZE_RATIO", "0.005"))  # 0.5% of frame
MAX_SIZE_RATIO = float(os.getenv("MAX_SIZE_RATIO", "0.6"))    # 60% of frame

# Position filter: water zone ratio (fraction of frame height from bottom)
WATER_ZONE_RATIO = float(os.getenv("WATER_ZONE_RATIO", "0.8"))  # 80% from bottom

# ===== Tracking Configuration =====
# Maximum time (seconds) without detection before removing a track
MAX_STALENESS = float(os.getenv("MAX_STALENESS", "1.0"))

# IOU threshold for track-to-detection association
TRACKER_IOU_THRESHOLD = float(os.getenv("TRACKER_IOU_THRESHOLD", "0.2"))

# ===== Video Input Configuration =====
# Default video source (can be overridden via command line argument)
DEFAULT_VIDEO_SOURCE = os.path.join(
    Path(__file__).parent.parent, 
    "tests/data/Video_Generation_of_Beach_Swimming.mp4"
)

# Output FPS for processing
OUTPUT_FPS = int(os.getenv("OUTPUT_FPS", "10"))

# ===== Backend Configuration =====
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
CAMERA_ID = os.getenv("CAMERA_ID", "cam_001")
SEND_TO_BACKEND = os.getenv("SEND_TO_BACKEND", "true").lower() == "true"
BACKEND_SEND_INTERVAL = int(os.getenv("BACKEND_SEND_INTERVAL", "1"))  # Send every N frames

# ===== Display Configuration =====
SHOW_WINDOW = os.getenv("SHOW_WINDOW", "false").lower() == "true"  # OpenCV window

# ===== Heatmap Configuration =====
HEATMAP_SIZE = (360, 640)  # (height, width)
HEATMAP_DECAY = float(os.getenv("HEATMAP_DECAY", "0.98"))  # How quickly heatmap fades
HEATMAP_GAUSS_SIGMA = int(os.getenv("HEATMAP_GAUSS_SIGMA", "12"))  # Blur amount

# ===== Logging Configuration =====
LOG_FILE = os.getenv("LOG_FILE", "tracking_log.csv")

