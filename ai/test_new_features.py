"""
Quick test script for new analysis features
"""
import cv2
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from water_analyzer import WaterAnalyzer
from behavior_analyzer import BehaviorAnalyzer
from risk_engine import RiskEngine, RiskLevel
from detector import Detector
from tracker import PersonTracker
from filter import apply_all_filters

print("="*60)
print("🧪 TESTING NEW ANALYSIS FEATURES")
print("="*60)

# Test video path
video_path = Path(__file__).parent.parent / "tests/data/Video_Generation_of_Beach_Swimming.mp4"

if not video_path.exists():
    print(f"❌ Video not found: {video_path}")
    sys.exit(1)

print(f"📹 Opening video: {video_path}")
cap = cv2.VideoCapture(str(video_path))

if not cap.isOpened():
    print("❌ Could not open video")
    sys.exit(1)

# Read first frame
ret, frame = cap.read()
if not ret:
    print("❌ Could not read frame")
    sys.exit(1)

print(f"✅ Frame shape: {frame.shape}")

# Initialize components
print("\n🔧 Initializing components...")
detector = Detector(model_type="yolo", model_name="yolov8n.pt")
print("✅ Detector initialized")

water_analyzer = WaterAnalyzer(frame_shape=frame.shape[:2])
print("✅ Water analyzer initialized")

behavior_analyzer = BehaviorAnalyzer()
print("✅ Behavior analyzer initialized")

risk_engine = RiskEngine()
print("✅ Risk engine initialized")

tracker = PersonTracker()
print("✅ Tracker initialized")

# Test water analysis
print("\n🌊 Testing water analysis...")
water_conditions = water_analyzer.analyze_conditions(frame)
print(f"   Has water: {water_conditions.has_water}")
print(f"   Water confidence: {water_conditions.water_confidence:.2f}")
print(f"   Visibility: {water_conditions.visibility_estimate:.2f}")
print(f"   Wave activity: {water_conditions.wave_activity:.2f}")
print(f"   Calm score: {water_conditions.calm_score:.2f}")

# Test detection and tracking on first few frames
print("\n👥 Testing detection and tracking...")
frame_count = 0
max_frames = 10

while frame_count < max_frames:
    ret, frame = cap.read()
    if not ret:
        break
    
    # Detect
    detections = detector.detect_people(frame, conf_thres=0.5)
    filtered = apply_all_filters(detections, frame, frame.shape[:2], strict_mode=False)
    
    # Track
    tracked = tracker.update(filtered, timestamp=frame_count * 0.1)
    
    if tracked:
        print(f"\n   Frame {frame_count}: Found {len(tracked)} swimmers")
        
        for person in tracked:
            # Get zone
            zone = water_analyzer.get_zone_for_bbox(person.bbox)
            
            # Analyze behavior
            motion = behavior_analyzer.update(
                person.track_id,
                person.bbox,
                frame_count * 0.1,
                frame_count
            )
            
            # Get distance from shore
            distance = behavior_analyzer.get_distance_from_shore(
                person.track_id,
                frame.shape[0]
            )
            
            # Calculate risk
            risk = risk_engine.calculate_risk(
                person.track_id,
                zone,
                motion,
                distance,
                frame_count * 0.1
            )
            
            print(f"      Track {person.track_id}: Zone={zone.value}, "
                  f"Pattern={motion.pattern.value}, "
                  f"Velocity={motion.velocity:.1f}px/s, "
                  f"Risk={risk.total_score:.0f} ({risk.level.value})")
    
    frame_count += 1

cap.release()

# Summary
print("\n" + "="*60)
print("📊 TEST SUMMARY")
print("="*60)
print(f"✅ Processed {frame_count} frames")
print(f"✅ Active tracks: {len(tracker.first_seen)}")
print(f"✅ Risk scores calculated: {len(risk_engine.risk_scores)}")
active_alerts = risk_engine.get_active_alerts()
print(f"✅ Active alerts: {len(active_alerts)}")

if active_alerts:
    print("\n🚨 Active Alerts:")
    for alert in active_alerts:
        print(f"   Track {alert.track_id}: Risk {alert.total_score:.0f} - {alert.level.value}")

print("\n✅ All tests completed successfully!")
print("="*60)

