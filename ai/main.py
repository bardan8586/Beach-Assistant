"""
Main script: Real-time swimmer tracking and heatmap visualization pipeline.

Pipeline:
    1. Acquire frames from RTSP (or local) video using RTSPVideoStream.
    2. Run per-frame YOLOv8 detector to find people.
    3. Track detected swimmers with PersonTracker (ByteTrack via Norfair).
    4. Update a spatial activity heatmap for visualization.
    5. Render bounding boxes/tracks and heatmap overlay.
    6. Display annotated frame in real-time.
    7. Log per-frame tracking data to CSV.

Modular, robust to dropped frames, no ML logic/risk engine yet.
"""

import cv2
import time
import csv
import os

# --- Import pipeline components ---
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from video_input import RTSPVideoStream
from detector import load_yolov8_model, detect_people
from tracker import PersonTracker
from heatmap import HeatmapAccumulator

# --------- Configurations ---------
# For testing: use the test video
import os
if len(sys.argv) > 1:
    RTSP_URL = sys.argv[1]
else:
    # Default to test video
    RTSP_URL = os.path.join(Path(__file__).parent.parent, "tests/data/beach_test.mp4")

OUTPUT_FPS = 10
HEATMAP_SIZE = (360, 640)    # Heatmap resolution (height, width), can match video or be smaller
DECAY = 0.98                 # How quickly heatmap "forgets" old activity (1.0=no decay, <1.0=temporal fade)
GAUSS_SIGMA = 12             # Blur for heatmap overlay
LOG_FILE = "tracking_log.csv"

# --- Initialize modules ---
print("Loading YOLOv8 model...")
yolo_model = load_yolov8_model()

print("Initializing person tracker...")
tracker = PersonTracker()

# Check if using RTSP or local file
use_rtsp = RTSP_URL.startswith("rtsp://")

if use_rtsp:
    print("Starting RTSP video stream...")
    video_stream = RTSPVideoStream(RTSP_URL, output_fps=OUTPUT_FPS)
    # Wait for first frame (with timeout)
    frame, frame_timestamp = None, None
    while frame is None:
        frame, frame_timestamp = video_stream.read(timeout=2.0)
        if frame is None:
            print("Waiting for video feed...")
            time.sleep(2)
        else:
            break
else:
    print(f"Opening local video: {RTSP_URL}")
    video_stream = cv2.VideoCapture(RTSP_URL)
    if not video_stream.isOpened():
        print(f"ERROR: Could not open video: {RTSP_URL}")
        sys.exit(1)
    ret, frame = video_stream.read()
    if not ret:
        print("ERROR: Could not read first frame")
        sys.exit(1)
    frame_timestamp = time.time()

FRAME_SHAPE = frame.shape
print(f"First frame shape: {FRAME_SHAPE}")

print("Setting up heatmap accumulator...")
heatmap_acc = HeatmapAccumulator(frame_shape=FRAME_SHAPE,
                                out_size=HEATMAP_SIZE,
                                decay=DECAY,
                                gauss_sigma=GAUSS_SIGMA)

# Prepare logging
log_fields = ["frame_idx", "track_id", "x1", "y1", "x2", "y2", "timestamp"]
if not os.path.exists(LOG_FILE) or os.path.getsize(LOG_FILE) == 0:
    with open(LOG_FILE, "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(log_fields)

# --- Main pipeline loop ---
cv2.namedWindow("Swimmer Tracking", cv2.WINDOW_NORMAL)
frame_idx = 0
fps_counter = 0
fps_timer = time.time()
current_fps = 0

print("\n" + "="*60)
print("🏖️  BEACH SAFETY AI - FULL PIPELINE RUNNING")
print("="*60)
print("Press 'q' or ESC to quit")
print("="*60 + "\n")

try:
    while True:
        # --- a. Capture frame ---
        if use_rtsp:
            frame, frame_timestamp = video_stream.read(timeout=1.0)
            if frame is None:
                print("Frame dropped or camera issue -- skipping.")
                time.sleep(0.1)
                continue
        else:
            ret, frame = video_stream.read()
            if not ret:
                print("\n🏁 End of video reached")
                break
            frame_timestamp = time.time()

        orig_frame = frame.copy()

        # --- b. Detect swimmers ---
        detections = detect_people(yolo_model, frame)
        # Format: [(x1, y1, x2, y2, conf), ...]

        # --- c. Track swimmers ---
        tracked_people = tracker.update(detections, timestamp=frame_timestamp)
        # tracked_people: List[TrackedPerson] (has .track_id, .bbox, ...)

        # --- d. Update heatmap ---
        heatmap_acc.update(tracked_people, frame_idx)

        # --- e. Draw bounding boxes and track IDs ---
        for person in tracked_people:
            x1, y1, x2, y2 = person.bbox
            color = (0, 255, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label = f"ID {person.track_id}"
            cv2.putText(frame, label, (x1, y1-8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        # --- f. Overlay heatmap on frame ---
        frame_with_overlay = heatmap_acc.render_overlay(frame, alpha=0.5)
        
        # --- FPS calculation ---
        fps_counter += 1
        if time.time() - fps_timer > 1.0:
            current_fps = fps_counter / (time.time() - fps_timer)
            fps_counter = 0
            fps_timer = time.time()
        
        # --- Add info overlay ---
        info_text = f"Frame: {frame_idx} | Swimmers: {len(tracked_people)} | FPS: {current_fps:.1f}"
        cv2.putText(frame_with_overlay, info_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame_with_overlay, info_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 1)

        # --- g. Display the frame ---
        cv2.imshow("Swimmer Tracking", frame_with_overlay)
        
        # Console output every 30 frames
        if frame_idx % 30 == 0:
            print(f"Frame {frame_idx:4d} | Swimmers: {len(tracked_people):2d} | "
                  f"FPS: {current_fps:.1f} | Logged: {len(tracked_people)} tracks")

        # --- h. Logging per-frame tracking data ---
        # Write each tracked person with timestamp
        with open(LOG_FILE, "a", newline='') as f:
            writer = csv.writer(f)
            for person in tracked_people:
                x1, y1, x2, y2 = person.bbox
                writer.writerow([
                    frame_idx,
                    person.track_id,
                    x1, y1, x2, y2,
                    frame_timestamp
                ])

        # FPS control: keep up to OUTPUT_FPS
        key = cv2.waitKey(int(1000 // OUTPUT_FPS)) & 0xFF
        if key == 27 or key == ord('q'):
            print("Exiting main loop.")
            break

        frame_idx += 1

except KeyboardInterrupt:
    print("Interrupted. Exiting...")

finally:
    if use_rtsp:
        video_stream.stop()
    else:
        video_stream.release()
    cv2.destroyAllWindows()
    print("\n" + "="*60)
    print("📊 PIPELINE COMPLETED")
    print("="*60)
    print(f"Total frames processed: {frame_idx}")
    print(f"Tracking log saved to: {LOG_FILE}")
    print("="*60)

# ----
# Explanations:
# - Data flows from camera (video input) --> detection (yolo) --> tracking (assigns ID) --> heatmap (activity map).
# - Each component is a modular Python object or function (see ai/ directory).
# - Tracking results and bounding boxes are rendered for visual debugging.
# - All tracking results are logged per-frame to CSV for later ML labeling, training or analysis.
# - Heatmap overlay gives high-level swimmer traffic "hotspots" in the pool.
# - Pipeline is robust: dropped frames/camera issues cause a warning, but system continues (does not crash).
# ----
