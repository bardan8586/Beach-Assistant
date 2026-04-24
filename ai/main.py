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
import requests
import json
import numpy as np

# --- Import pipeline components ---
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from video_input import RTSPVideoStream
from detector import Detector, load_yolov8_model, detect_people  # Support both new and legacy
from tracker import PersonTracker
from heatmap import HeatmapAccumulator
from filter import apply_all_filters
from water_analyzer import WaterAnalyzer, WaterZone
from behavior_analyzer import BehaviorAnalyzer, MovementPattern
from risk_engine import RiskEngine, RiskLevel
from scene_analyzer import SceneAnalyzer
from pose_analyzer import PoseAnalyzer, SwimmingAction  # Pose-based drowning detection
from advanced_tracker import AdvancedTracker  # Robust tracking for ocean conditions
from temporal_analyzer import TemporalAnalyzer, SwimmerState  # Fatigue & panic progression
from beach_calibration import BeachCalibration  # Learn beach-specific patterns
from alert_engine import AlertEngine, AlertLevel  # NEW: Intelligent alert system with hysteresis

# --------- Configurations ---------
# For testing: use the test video (CLI path, or first video in tests/data)
if len(sys.argv) > 1:
    RTSP_URL = sys.argv[1]
else:
    data_dir = Path(__file__).parent.parent / "tests" / "data"
    default_video = data_dir / "Video_Generation_of_Beach_Swimming.mp4"
    if default_video.exists():
        RTSP_URL = str(default_video)
    else:
        # Use first video found in tests/data
        for ext in ("*.mp4", "*.avi", "*.mov", "*.mkv"):
            videos = list(data_dir.glob(ext))
            if videos:
                RTSP_URL = str(videos[0])
                print(f"Using video from data folder: {videos[0].name}")
                break
        else:
            RTSP_URL = str(default_video)  # Will fail with clear path in error

OUTPUT_FPS = 10
HEATMAP_SIZE = (360, 640)    # Heatmap resolution (height, width), can match video or be smaller
DECAY = 0.98                 # How quickly heatmap "forgets" old activity (1.0=no decay, <1.0=temporal fade)
GAUSS_SIGMA = 12             # Blur for heatmap overlay
LOG_FILE = "tracking_log.csv"

# System mode configuration
SYSTEM_MODE = os.getenv("SYSTEM_MODE", "playback")  # "playback" or "live"
if SYSTEM_MODE not in ["playback", "live"]:
    print(f"⚠️  Invalid SYSTEM_MODE: {SYSTEM_MODE}, defaulting to 'playback'")
    SYSTEM_MODE = "playback"

# Performance optimizations
FRAME_SKIP = int(os.getenv("FRAME_SKIP", "2"))  # Process every Nth frame (1=all, 2=every other)
MULTI_SCALE_DETECTION = os.getenv("MULTI_SCALE_DETECTION", "false").lower() == "true"

# Backend API configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
CAMERA_ID = os.getenv("CAMERA_ID", "cam_001")
SEND_TO_BACKEND = os.getenv("SEND_TO_BACKEND", "true").lower() == "true"
BACKEND_SEND_INTERVAL = 1  # Send to backend every frame for real-time updates
SHOW_WINDOW = os.getenv("SHOW_WINDOW", "false").lower() == "true"  # Disable OpenCV window for web mode

# --- Initialize modules ---
# Use config so we default to fine-tuned best.pt when it exists (assessment / production)
from config import DETECTOR_TYPE, MODEL_NAME
print(f"Initializing detector: {DETECTOR_TYPE}...")
print(f"Model: {MODEL_NAME}")
# Enable pose estimation for drowning detection
ENABLE_POSE = os.getenv("ENABLE_POSE", "true").lower() == "true"

if DETECTOR_TYPE == "roboflow":
    detector = Detector(
        model_type="roboflow",
        roboflow_api_key=os.getenv("ROBOFLOW_API_KEY"),
        roboflow_model_id=os.getenv("ROBOFLOW_MODEL_ID"),
        roboflow_version=int(os.getenv("ROBOFLOW_VERSION", "1")),
        enable_pose=ENABLE_POSE  # NEW: Enable pose estimation
    )
    yolo_model = detector  # Use detector directly
else:
    # Use YOLOv8 (default) - create Detector instance for unified API
    detector = Detector(model_type="yolo", model_name=MODEL_NAME, enable_pose=ENABLE_POSE)
    yolo_model = detector  # Use detector directly

if ENABLE_POSE:
    print("✅ Pose estimation enabled for drowning detection")

print("Initializing person tracker...")
tracker = PersonTracker()

print("Initializing behavior analyzer...")
behavior_analyzer = BehaviorAnalyzer()

print("Initializing risk engine...")
risk_engine = RiskEngine()

print("Initializing pose analyzer for drowning detection...")
pose_analyzer = PoseAnalyzer() if ENABLE_POSE else None

print("Initializing advanced tracker for occlusion handling...")
advanced_tracker = AdvancedTracker(max_occlusion_frames=30)  # Keep track for 3 seconds after disappearing

print("Initializing temporal analyzer for fatigue & panic detection...")
temporal_analyzer = TemporalAnalyzer()

print("Initializing beach calibration system...")
beach_calibration = BeachCalibration(beach_id=CAMERA_ID, calibration_samples_needed=100)
# Try to load existing calibration
calibration_file = f"beach_profile_{CAMERA_ID}.pkl"
if not beach_calibration.load_profile(calibration_file):
    print(f"📚 Starting NEW calibration for beach '{CAMERA_ID}'")
    print(f"   Will analyze first ~100 swimmers to learn normal patterns")

print("Initializing intelligent alert system...")
alert_engine = AlertEngine()
print("✅ Alert engine ready with hysteresis and throttling")

# Water analyzer will be initialized after we get first frame
water_analyzer = None

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

print("Initializing scene analyzer...")
scene_analyzer = SceneAnalyzer(frame_shape=FRAME_SHAPE[:2])
scene_geometry = scene_analyzer.analyze_scene(frame)
print(f"✅ Shore line detected at Y={scene_geometry.shore_line_y}")
print(f"✅ Horizon detected at Y={scene_geometry.horizon_y}")

print("Initializing water analyzer...")
water_analyzer = WaterAnalyzer(frame_shape=FRAME_SHAPE[:2], 
                               shore_line_y=scene_geometry.shore_line_y)

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
if SHOW_WINDOW:
    cv2.namedWindow("Swimmer Tracking", cv2.WINDOW_NORMAL)
frame_idx = 0
fps_counter = 0
fps_timer = time.time()
current_fps = 0

print("\n" + "="*60)
print("🏖️  BEACH SAFETY AI - FULL PIPELINE RUNNING")
print("="*60)
print(f"Mode: {SYSTEM_MODE.upper()}")
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
            # Use VIDEO time (ms → s) so web app overlay sync works; wall clock breaks sync
            frame_timestamp = video_stream.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            if frame_timestamp <= 0 and frame_idx > 0:
                # Fallback if CAP_PROP_POS_MSEC not reliable
                fps = video_stream.get(cv2.CAP_PROP_FPS) or 30
                frame_timestamp = frame_idx / fps

        # ⚡ PERFORMANCE: Frame skipping (2x-3x speedup)
        # IMPORTANT: Increment frame_idx BEFORE skip check, or we'll skip forever!
        if FRAME_SKIP > 1 and frame_idx % FRAME_SKIP != 0:
            frame_idx += 1  # ✅ Increment even for skipped frames
            continue  # Skip this frame, process next one

        orig_frame = frame.copy()

        # --- b. Detect swimmers ---
        try:
            # ⚡ PERFORMANCE: Conditional multi-scale detection
            if isinstance(yolo_model, Detector):
                # First pass: normal confidence
                raw_detections = yolo_model.detect_people(frame, conf_thres=0.5)
                
                # Second pass: ONLY if multi-scale is enabled (slow but catches far swimmers)
                if MULTI_SCALE_DETECTION:
                    far_detections = yolo_model.detect_people(frame, conf_thres=0.3, min_size=20)
                    all_detections = raw_detections + far_detections
                else:
                    all_detections = raw_detections
                # Improved deduplication using IoU (Intersection over Union)
                filtered_detections = []
                for det in all_detections:
                    x1, y1, x2, y2, conf = det[0], det[1], det[2], det[3], det[4]
                    is_duplicate = False
                    box_area = (x2 - x1) * (y2 - y1)
                    for existing in filtered_detections:
                        ex1, ey1, ex2, ey2, econf = existing[0], existing[1], existing[2], existing[3], existing[4]
                        # Calculate IoU
                        intersection_x = max(0, min(x2, ex2) - max(x1, ex1))
                        intersection_y = max(0, min(y2, ey2) - max(y1, ey1))
                        intersection_area = intersection_x * intersection_y
                        
                        existing_area = (ex2 - ex1) * (ey2 - ey1)
                        union_area = box_area + existing_area - intersection_area
                        iou = intersection_area / union_area if union_area > 0 else 0
                        
                        # If IoU > 0.5, consider it a duplicate
                        if iou > 0.5:
                            if conf > econf:
                                filtered_detections.remove(existing)
                            else:
                                is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        filtered_detections.append(det)
                raw_detections = filtered_detections
            else:
                raw_detections = detect_people(yolo_model, frame, conf_thres=0.5)
            # Format: [(x1, y1, x2, y2, conf), ...]
            
            # --- b.1 Apply filters to improve accuracy ---
            detections = apply_all_filters(
                raw_detections, 
                frame, 
                FRAME_SHAPE,
                strict_mode=False  # Don't require water detection (too strict for some videos)
            )
        except Exception as e:
            if frame_idx % 60 == 0:  # Log errors occasionally
                print(f"⚠️  Detection error: {e}")
            detections = []  # Continue with empty detections

        # --- c. Track swimmers ---
        tracked_people = tracker.update(detections, timestamp=frame_timestamp)
        # tracked_people: List[TrackedPerson] (has .track_id, .bbox, ...)
        
        # --- c.1 SMART STAGED ANALYSIS: Only run pose on high-risk swimmers ---
        # First, do quick risk assessment on ALL swimmers (cheap)
        quick_risk_scores = {}
        high_risk_swimmers = []  # Swimmers that need deep pose analysis
        
        for person in tracked_people:
            # Get basic risk factors (fast)
            zone = water_analyzer.get_zone_for_bbox(person.bbox)
            motion_metrics = behavior_analyzer.get_motion_metrics(person.track_id)
            
            # Quick risk score (without pose)
            quick_risk = 0.0
            if zone == WaterZone.DANGER:
                quick_risk += 30
            elif zone == WaterZone.CAUTION:
                quick_risk += 15
            
            if motion_metrics and motion_metrics.pattern in [MovementPattern.STATIONARY, MovementPattern.ERRATIC]:
                quick_risk += 25
            
            quick_risk_scores[person.track_id] = quick_risk
            
            # 🎯 SMART FILTER: Only analyze pose if risk > 30 OR in danger zone
            if quick_risk > 30 or zone == WaterZone.DANGER:
                high_risk_swimmers.append(person)
        
        # --- c.2 Deep pose analysis (ONLY for high-risk swimmers) ---
        poses_dict = {}  # track_id -> (features, action, keypoints)
        if ENABLE_POSE and pose_analyzer and len(high_risk_swimmers) > 0:
            try:
                print(f"🎯 Analyzing pose for {len(high_risk_swimmers)}/{len(tracked_people)} high-risk swimmers")
                
                # Detect all poses in the frame (unavoidable, YOLOv8-Pose processes whole frame)
                all_poses = detector.detect_poses(frame, conf_thres=0.4)
                
                # Match poses ONLY to high-risk swimmers (optimization on matching)
                for i, keypoints in all_poses.items():
                    if len(keypoints) > 0:
                        # Get pose centroid (average of visible keypoints)
                        visible_kp = keypoints[keypoints[:, 2] > 0.3][:, :2]  # x, y only, conf > 0.3
                        if len(visible_kp) > 0:
                            pose_center = visible_kp.mean(axis=0)
                            
                            # Find closest HIGH-RISK person (not all people!)
                            min_dist = float('inf')
                            closest_person = None
                            for person in high_risk_swimmers:
                                x1, y1, x2, y2 = person.bbox
                                bbox_center = np.array([(x1 + x2) / 2, (y1 + y2) / 2])
                                dist = np.linalg.norm(pose_center - bbox_center)
                                if dist < min_dist:
                                    min_dist = dist
                                    closest_person = person
                            
                            # If close enough, analyze pose
                            if closest_person and min_dist < 150:  # Within 150 pixels
                                features, action = pose_analyzer.analyze_pose(keypoints, closest_person.track_id)
                                poses_dict[closest_person.track_id] = (features, action, keypoints)
            except Exception as e:
                if frame_idx % 30 == 0:  # Log occasionally
                    print(f"⚠️  Pose analysis error: {e}")
        
        # --- c.2 Analyze water conditions ---
        water_conditions = water_analyzer.analyze_conditions(frame)
        
        # --- c.3 Update advanced tracking features (appearance, trajectory) ---
        for person in tracked_people:
            # Update appearance features for re-identification
            advanced_tracker.update_appearance(person.track_id, orig_frame, person.bbox, frame_idx)
            
            # Update trajectory history
            x1, y1, x2, y2 = person.bbox
            center = ((x1 + x2) // 2, (y1 + y2) // 2)
            advanced_tracker.update_trajectory(person.track_id, center, frame_timestamp)
        
        # --- c.4 Analyze swimmer behavior and calculate risk ---
        active_track_ids = []
        active_alerts_temp = []  # Collect alerts during processing
        for person in tracked_people:
            active_track_ids.append(person.track_id)
            
            # Get zone for this swimmer
            zone = water_analyzer.get_zone_for_bbox(person.bbox)
            
            # Analyze behavior
            motion_metrics = behavior_analyzer.update(
                person.track_id,
                person.bbox,
                frame_timestamp,
                frame_idx
            )
            
            # Calculate distance from shore
            distance_from_shore = behavior_analyzer.get_distance_from_shore(
                person.track_id,
                FRAME_SHAPE[0]
            )
            
            # 🌊 Detect if swimmer is drifting (rip current)
            is_drifting, drift_speed = advanced_tracker.detect_drift(
                person.track_id,
                scene_geometry.shore_line_y if scene_geometry else FRAME_SHAPE[0]
            )
            
            # 🆕 Extract pose-based action FIRST (needed for temporal analysis)
            pose_risk = 0.0
            swimming_action = None
            if person.track_id in poses_dict:
                features, action, _ = poses_dict[person.track_id]
                pose_risk = pose_analyzer.get_drowning_risk_from_pose(action, features)
                swimming_action = action
                
                # 🚨 CRITICAL: If pose indicates active/passive drowning, MAX OUT risk
                if action in [SwimmingAction.ACTIVE_DROWNING, SwimmingAction.PASSIVE_DROWNING]:
                    pose_risk = 95.0  # CRITICAL
            
            # ⏱️ Temporal analysis (fatigue, panic progression) - uses swimming_action
            swimmer_state, state_transition = temporal_analyzer.update(
                track_id=person.track_id,
                position=((x1 + x2) // 2, (y1 + y2) // 2),
                speed=motion_metrics.velocity if motion_metrics else 0.0,
                zone=zone.value if zone else "safe",
                pose_action=swimming_action.value if swimming_action else None,
                timestamp=frame_timestamp
            )
            
            # Get panic progression score (0-100)
            panic_score = temporal_analyzer.get_panic_progression_score(person.track_id)
            
            # Get fatigue metrics
            fatigue_metrics = temporal_analyzer.get_fatigue_metrics(person.track_id, frame_timestamp)
            
            # 🏖️ Feed observation to beach calibration
            if not beach_calibration.profile.is_calibrated:
                beach_calibration.add_observation(
                    swimmer_id=person.track_id,
                    position=((x1 + x2) // 2, (y1 + y2) // 2),
                    speed=motion_metrics.velocity if motion_metrics else 0.0,
                    zone=zone.value if zone else "safe",
                    risk_level="low",  # Will get real risk_level after it's calculated
                    timestamp=frame_timestamp,
                    is_exiting=False  # Would detect this in full version
                )
            
            # Calculate combined risk score (integrating pose risk + temporal panic)
            # Use highest of: pose_risk, panic_score
            final_risk_override = None
            if pose_risk > 50 or panic_score > 50:
                final_risk_override = max(pose_risk, panic_score)
            
            risk_score = risk_engine.calculate_risk(
                person.track_id,
                zone,
                motion_metrics,
                distance_from_shore,
                frame_timestamp,
                pose_risk_override=final_risk_override
            )
            
            # 🚨 NEW: Use intelligent alert engine (with hysteresis & throttling)
            alert = alert_engine.update(
                swimmer_id=person.track_id,
                risk_score=risk_score.total_score if risk_score else 0,
                risk_level=risk_score.level.value if risk_score else "low",
                swimmer_state=swimmer_state.value,
                reason=risk_score.factors if risk_score and risk_score.factors else {},
                location=((x1 + x2) // 2, (y1 + y2) // 2),
                zone=zone.value if zone else "safe",
                timestamp=frame_timestamp,
                pose_action=swimming_action.value if swimming_action else None
            )
            
            if alert:
                active_alerts_temp.append(alert)
        
        # Get all active alerts from alert engine
        active_alerts = alert_engine.get_active_alerts()
        
        # Cleanup inactive tracks
        behavior_analyzer.cleanup(active_track_ids)
        risk_engine.cleanup(active_track_ids)
        advanced_tracker.cleanup(active_track_ids)
        temporal_analyzer.cleanup(active_track_ids)
        alert_engine.cleanup(active_track_ids)

        # --- c.1 Send data to backend API (every N frames) ---
        if SEND_TO_BACKEND and frame_idx % BACKEND_SEND_INTERVAL == 0:
            try:
                from datetime import datetime
                
                # Build swimmers list in FrameResult format
                swimmers_data = []
                for person in tracked_people:
                    x1, y1, x2, y2 = person.bbox
                    
                    # Get additional analysis data
                    risk_score = risk_engine.get_risk_score(person.track_id)
                    zone = water_analyzer.get_zone_for_bbox(person.bbox)
                    motion_metrics = behavior_analyzer.get_motion_metrics(person.track_id)
                    pattern = behavior_analyzer.get_pattern(person.track_id)
                    
                    # Get time in water (seconds)
                    first_seen_ts = tracker.first_seen.get(person.track_id, frame_timestamp)
                    time_in_water = frame_timestamp - first_seen_ts if isinstance(first_seen_ts, (int, float)) else 0.0
                    
                    swimmer_data = {
                        "track_id": person.track_id,
                        "bbox": {
                            "x": int(x1),
                            "y": int(y1),
                            "w": int(x2 - x1),
                            "h": int(y2 - y1)
                        },
                        "confidence": float(person.confidence),
                        "risk_score": int(risk_score.total_score) if risk_score else 0,
                        "risk_level": risk_score.level.value.upper() if risk_score else "LOW",
                        "behavior": pattern.value.upper() if pattern else "NORMAL",
                        "zone": zone.value.upper() if zone else "SAFE",
                        "time_in_water": float(time_in_water),
                        "velocity": float(motion_metrics.velocity) if motion_metrics else 0.0
                    }
                    
                    swimmers_data.append(swimmer_data)
                
                # Build alerts list from alert engine
                alerts_data = []
                for alert in alert_engine.get_active_alerts():
                    alerts_data.append({
                        "alert_id": alert.alert_id,
                        "swimmer_id": alert.swimmer_id,
                        "level": alert.level.value,
                        "reason": alert.reason.value,
                        "risk_score": float(alert.risk_score),
                        "timestamp": float(alert.timestamp),
                        "location": list(alert.location),
                        "zone": alert.zone,
                        "duration": float(alert.duration),
                        "confidence": float(alert.confidence),
                        "context": alert.context,
                        "action_recommended": alert.action_recommended,
                        "acknowledged": alert.acknowledged
                    })
                
                # Build FrameResult payload
                # Use VIDEO_ID from backend when processing uploaded video (so playback finds results)
                video_id_for_ingest = os.getenv("VIDEO_ID", "realtime")
                payload = {
                    "video_id": video_id_for_ingest,
                    "camera_id": CAMERA_ID,
                    "frame_index": frame_idx,
                    "timestamp_ms": int(frame_timestamp * 1000),  # Convert seconds to milliseconds
                    "video_width": FRAME_SHAPE[1],  # width
                    "video_height": FRAME_SHAPE[0],  # height
                    "swimmers": swimmers_data,
                    "scene": {
                        "shore_line_y": scene_geometry.shore_line_y if scene_geometry else None,
                        "horizon_y": scene_geometry.horizon_y if scene_geometry else None,
                        "water_percentage": water_conditions.water_confidence * 100 if water_conditions else 0.0,
                        "visibility": water_conditions.visibility_estimate if water_conditions else 0.0,
                        "wave_activity": water_conditions.wave_activity if water_conditions else 0.0,
                        "calm_score": water_conditions.calm_score if water_conditions else 0.0
                    },
                    "metrics": {
                        "fps": current_fps,
                        "latency_ms": int((time.time() - frame_timestamp) * 1000),
                        "detections_raw": len(raw_detections),
                        "detections_filtered": len(detections),
                        "active_tracks": len(tracked_people)
                    },
                    "alerts": alerts_data,  # NEW: Include intelligent alerts
                    "system_mode": SYSTEM_MODE
                }
                
                response = requests.post(
                    f"{BACKEND_URL}/api/data/ingest",
                    json=payload,
                    timeout=1.0  # Don't block if backend is slow
                )
                if response.status_code == 200:
                    if frame_idx % 30 == 0:  # Log every 30 frames
                        print(f"✅ Sent FrameResult: {len(swimmers_data)} swimmers, {FRAME_SHAPE[1]}x{FRAME_SHAPE[0]} (Frame {frame_idx})")
            except requests.exceptions.ConnectionError:
                if frame_idx == 0 or frame_idx % 60 == 0:  # Warn on first frame and every 60 frames
                    print(f"⚠️  Backend not reachable at {BACKEND_URL}")
                    print(f"   Make sure backend is running: cd backend && python -m app.main")
            except Exception as e:
                if frame_idx % 60 == 0:  # Only log errors occasionally
                    print(f"⚠️  Failed to send to backend: {e}")

        # --- d. Update heatmap ---
        heatmap_acc.update(tracked_people, frame_idx)

        # --- e. Update scene geometry periodically (for both web and window mode) ---
        # Update scene geometry periodically to adapt to changing conditions
        if frame_idx % 30 == 0:  # Update every 30 frames
            scene_geometry = scene_analyzer.analyze_scene(frame)
            water_analyzer.update_shore_line(scene_geometry.shore_line_y)
        
        # --- e.1 Draw scene geometry and water zones overlay (only if showing window) ---
        if SHOW_WINDOW:
            # Draw scene geometry (shore line, horizon)
            frame = scene_analyzer.draw_scene_geometry(frame, scene_geometry)
            # Draw water zones
            frame = water_analyzer.draw_zones(frame, alpha=0.4)
        
        # --- e.1 Draw bounding boxes with LIFEGUARD-FRIENDLY risk hierarchy ---
        # Sort by risk (HIGH first) so they're drawn on top
        swimmers_by_risk = sorted(tracked_people, 
                                 key=lambda p: risk_engine.get_risk_score(p.track_id).total_score if risk_engine.get_risk_score(p.track_id) else 0)
        
        for person in swimmers_by_risk:
            x1, y1, x2, y2 = person.bbox
            
            # Get risk score and zone
            risk_score = risk_engine.get_risk_score(person.track_id)
            zone = water_analyzer.get_zone_for_bbox(person.bbox)
            
            # 🎨 CLEAR VISUAL HIERARCHY for Lifeguards
            is_high_risk = risk_score and risk_score.level == RiskLevel.HIGH
            is_medium_risk = risk_score and risk_score.level == RiskLevel.MEDIUM
            
            # Color: Simple Red/Yellow/Green
            if is_high_risk:
                color = (0, 0, 255)  # 🔴 RED - URGENT
                thickness = 4  # Extra thick for visibility
                font_scale = 1.0  # Bigger label
            elif is_medium_risk:
                color = (0, 200, 255)  # 🟡 ORANGE - CAUTION
                thickness = 3
                font_scale = 0.8
            else:
                color = (0, 255, 0)  # 🟢 GREEN - OK
                thickness = 2
                font_scale = 0.6
            
            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
            
            # 🦴 POSE SKELETON: Only drawn for high-risk swimmers being analyzed
            if person.track_id in poses_dict:
                features, action, keypoints = poses_dict[person.track_id]
                
                # Visual indicator: "[POSE]" badge shows this swimmer is getting deep analysis
                cv2.putText(frame, "[POSE]", (x2 + 5, y1 + 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                
                # Define skeleton connections (COCO format)
                skeleton = [
                    (5, 6),   # shoulders
                    (5, 7), (7, 9),   # left arm
                    (6, 8), (8, 10),  # right arm
                    (5, 11), (6, 12), (11, 12),  # torso
                    (11, 13), (13, 15),  # left leg
                    (12, 14), (14, 16),  # right leg
                ]
                
                # Draw skeleton lines (thicker for drowning detection)
                skeleton_thickness = 3 if 'DROWNING' in action.value else 2
                for pt1_idx, pt2_idx in skeleton:
                    if keypoints[pt1_idx, 2] > 0.3 and keypoints[pt2_idx, 2] > 0.3:  # confidence threshold
                        pt1 = tuple(keypoints[pt1_idx, :2].astype(int))
                        pt2 = tuple(keypoints[pt2_idx, :2].astype(int))
                        cv2.line(frame, pt1, pt2, color, skeleton_thickness)
                
                # Draw keypoints (larger for key joints)
                for i, kp in enumerate(keypoints):
                    if kp[2] > 0.3:  # confidence threshold
                        x, y = int(kp[0]), int(kp[1])
                        # Larger circles for head (0), shoulders (5,6), hips (11,12)
                        radius = 5 if i in [0, 5, 6, 11, 12] else 3
                        cv2.circle(frame, (x, y), radius, color, -1)
                
                # Show action classification near the swimmer (BIG if drowning!)
                action_text = action.value.replace('_', ' ').upper()
                if 'DROWNING' in action_text:
                    action_color = (0, 0, 255)  # RED for drowning
                    action_scale = 0.8
                elif 'STRUGGLING' in action_text:
                    action_color = (0, 140, 255)  # ORANGE for struggling
                    action_scale = 0.7
                else:
                    action_color = (255, 255, 255)  # WHITE for normal
                    action_scale = 0.5
                
                cv2.putText(frame, action_text, (x1, y2 + 25), 
                           cv2.FONT_HERSHEY_SIMPLEX, action_scale, action_color, 2)
            
            # 📝 LABEL: Class (from model) + ID + State + Risk Level
            class_name = getattr(person, "class_name", "person")
            if risk_score:
                label = f"{class_name} #{person.track_id} {swimmer_state.value.upper()} {risk_score.level.value.upper()}"
            else:
                label = f"{class_name} #{person.track_id} {swimmer_state.value.upper()}"
            
            # ⏱️ Add FATIGUE indicator if detected
            if fatigue_metrics and fatigue_metrics.speed_trend < -0.3:
                label += " 💤TIRED"
                # Draw fatigue indicator
                cv2.putText(frame, f"Speed ↓{abs(fatigue_metrics.speed_trend)*100:.0f}%", 
                           (x1, y1 - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 165, 255), 1)
            
            # 🌊 Add DRIFT warning if detected
            if is_drifting and drift_speed > 10:
                label += " DRIFT!"
                # Draw drift arrow
                x1_center, y1_center = (x1 + x2) // 2, (y1 + y2) // 2
                arrow_len = int(drift_speed * 2)  # Visual arrow length
                cv2.arrowedLine(frame, (x1_center, y1_center), 
                              (x1_center, y1_center - arrow_len),
                              (0, 100, 255), 3, tipLength=0.3)
            
            # Label background for readability
            (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)
            cv2.rectangle(frame, (x1, y1 - label_h - 10), (x1 + label_w + 10, y1), color, -1)
            cv2.putText(frame, label, (x1 + 5, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 2)
            
            # 🎯 TRAJECTORY: Only show for MEDIUM/HIGH risk (reduce clutter)
            if is_medium_risk or is_high_risk:
                # Past trajectory (solid line)
                trajectory = behavior_analyzer.get_trajectory(person.track_id)
                if len(trajectory) > 1:
                    points = [(p.x, p.y) for p in trajectory[-10:]]  # Last 10 points only
                    for i in range(1, len(points)):
                        cv2.line(frame, points[i-1], points[i], color, 3 if is_high_risk else 2)
                
                # 🔮 NEW: Predicted trajectory (dashed line)
                predicted_traj = advanced_tracker.predict_trajectory(person.track_id, time_horizon=5.0)
                if predicted_traj and predicted_traj.confidence > 0.5:
                    # Draw predicted path as dashed line
                    pred_points = predicted_traj.positions
                    for i in range(1, len(pred_points)):
                        if i % 2 == 0:  # Dashed effect
                            cv2.line(frame, pred_points[i-1], pred_points[i], (255, 255, 0), 2)
                    
                    # Draw endpoint
                    if len(pred_points) > 0:
                        cv2.circle(frame, pred_points[-1], 6, (255, 255, 0), 2)
                        cv2.putText(frame, f"5s", pred_points[-1], 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
        
        # --- e.2 Draw active alerts - INTELLIGENT, NON-SPAMMY ---
        active_alerts = alert_engine.get_active_alerts()
        if active_alerts:
            alert_y = 90  # Start below calibration status
            for i, alert in enumerate(active_alerts[:3]):  # Show TOP 3 only
                # Color by severity
                if alert.level == AlertLevel.EMERGENCY:
                    bg_color = (0, 0, 200)     # Red
                    icon = "🚨"
                elif alert.level == AlertLevel.ALERT:
                    bg_color = (0, 140, 255)   # Orange
                    icon = "⚠️"
                else:  # WATCH
                    bg_color = (0, 200, 255)   # Yellow
                    icon = "👁️"
                
                # Alert text with context
                alert_text = f"{icon} #{alert.swimmer_id} {alert.level.value.upper()} ({alert.duration:.0f}s)"
                context_text = alert.action_recommended
                
                # Draw main alert
                (text_w, text_h), _ = cv2.getTextSize(alert_text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 3)
                cv2.rectangle(frame, (5, alert_y - text_h - 5), (text_w + 15, alert_y + 5), bg_color, -1)
                cv2.putText(frame, alert_text, (10, alert_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3)
                
                # Draw action recommendation below
                alert_y += text_h + 5
                cv2.putText(frame, context_text, (15, alert_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                alert_y += 25

        # --- f. Overlay heatmap on frame ---
        frame_with_overlay = heatmap_acc.render_overlay(frame, alpha=0.5)
        
        # --- FPS calculation ---
        fps_counter += 1
        if time.time() - fps_timer > 1.0:
            current_fps = fps_counter / (time.time() - fps_timer)
            fps_counter = 0
            fps_timer = time.time()
        
        # --- Add info overlay ---
        alert_summary = alert_engine.get_alert_summary()
        info_text = (f"Frame: {frame_idx} | Swimmers: {len(tracked_people)} | "
                    f"FPS: {current_fps:.1f} | Alerts: {alert_summary['emergency']}🔴 {alert_summary['alert']}🟠 {alert_summary['watch']}🟡")
        cv2.putText(frame_with_overlay, info_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame_with_overlay, info_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 1)
        
        # 🏖️ Show calibration progress if not yet calibrated
        if not beach_calibration.profile.is_calibrated:
            current, needed, progress = beach_calibration.get_calibration_progress()
            calib_text = f"📚 CALIBRATING: {current}/{needed} ({progress:.0f}%)"
            cv2.putText(frame_with_overlay, calib_text, (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        else:
            calib_text = f"✅ CALIBRATED ({beach_calibration.profile.calibration_samples} samples)"
            cv2.putText(frame_with_overlay, calib_text, (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Add water conditions info
        if water_conditions.has_water:
            water_text = (f"Water: Vis={water_conditions.visibility_estimate:.2f} | "
                         f"Waves={water_conditions.wave_activity:.2f} | "
                         f"Calm={water_conditions.calm_score:.2f}")
            cv2.putText(frame_with_overlay, water_text, (10, frame_with_overlay.shape[0] - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # --- g. Display the frame (only if SHOW_WINDOW is enabled) ---
        if SHOW_WINDOW:
            cv2.imshow("Swimmer Tracking", frame_with_overlay)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        # Console output every 30 frames with detailed stats
        if frame_idx % 30 == 0:
            # Calculate average confidence
            avg_conf = sum(d[4] for d in detections) / len(detections) if detections else 0.0
            
            # Get unique track IDs
            track_ids = [p.track_id for p in tracked_people]
            unique_tracks = len(set(track_ids))
            
            print(f"Frame {frame_idx:4d} | Raw: {len(raw_detections):2d} | "
                  f"Filtered: {len(detections):2d} | Swimmers: {len(tracked_people):2d} | "
                  f"Unique Tracks: {unique_tracks:2d} | Avg Conf: {avg_conf:.2f} | FPS: {current_fps:.1f}")
        
        # Detailed output every 100 frames
        if frame_idx % 100 == 0 and tracked_people:
            print(f"\n📊 Detailed Stats at Frame {frame_idx}:")
            print(f"   Active Swimmers: {len(tracked_people)}")
            for person in tracked_people[:5]:  # Show first 5
                x1, y1, x2, y2 = person.bbox
                time_in_view = person.last_seen - person.first_seen
                print(f"   Track #{person.track_id}: Conf={person.confidence:.2f}, "
                      f"Box=({x1},{y1},{x2},{y2}), Time={time_in_view:.1f}s")
            if len(tracked_people) > 5:
                print(f"   ... and {len(tracked_people) - 5} more swimmers")
            print()

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
    
    # 🏖️ Save beach calibration if complete
    if beach_calibration.profile.is_calibrated:
        beach_calibration.save_profile(calibration_file)
    
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
