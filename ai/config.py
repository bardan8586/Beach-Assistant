"""
Configuration file for Beach Safety AI Pipeline.

Set these via environment variables or modify defaults here.
"""

import os
from pathlib import Path

# ===== System Mode Configuration =====
# Mode: "playback" (uploaded videos, can pause/replay) or "live" (real-time camera, no replay)
SYSTEM_MODE = os.getenv("SYSTEM_MODE", "playback")  # Default: playback for development/training

# Validate system mode
if SYSTEM_MODE not in ["playback", "live"]:
    raise ValueError(f"SYSTEM_MODE must be 'playback' or 'live', got: {SYSTEM_MODE}")

# ===== Performance Optimization =====
# Frame skipping: Process every Nth frame (1=all frames, 2=every other, 3=every third)
# Higher = faster but less temporal resolution
FRAME_SKIP = int(os.getenv("FRAME_SKIP", "2"))  # Default: skip every other frame (2x speed)

# Multi-scale detection: Run 2 passes (normal + low confidence for far objects)
# Disable for 2x speed improvement
MULTI_SCALE_DETECTION = os.getenv("MULTI_SCALE_DETECTION", "false").lower() == "true"

# ===== Detection Configuration =====
# Detector type: "yolo" (local YOLOv8) or "roboflow" (Roboflow Inference API)
DETECTOR_TYPE = os.getenv("DETECTOR_TYPE", "yolo")

# YOLOv8 model selection (only used if DETECTOR_TYPE="yolo")
# Options: yolov8n.pt (nano), yolov8s.pt (small), or path to fine-tuned weights (e.g. runs/.../best.pt)
# If MODEL_NAME is not set, we use our fine-tuned Roboflow model when it exists, else yolov8s.pt
_FINETUNED_WEIGHTS = Path(__file__).resolve().parent / "runs" / "detect" / "runs-mai600" / "roboflow_v2_yolov8n_e5" / "weights" / "best.pt"
_MODEL_DEFAULT = str(_FINETUNED_WEIGHTS) if _FINETUNED_WEIGHTS.exists() else "yolov8s.pt"
MODEL_NAME = os.getenv("MODEL_NAME", _MODEL_DEFAULT)

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

