"""
Quick test without video input - just test if YOLOv8 loads correctly
"""

import numpy as np
import cv2
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "ai"))

from detector import load_yolov8_model, detect_people

print("\n" + "="*60)
print("🧪 QUICK SYSTEM TEST - YOLOv8 Detection")
print("="*60)

# Test 1: Model Loading
print("\n1️⃣  Testing Model Loading...")
try:
    model = load_yolov8_model("yolov8n.pt")
    print(f"   ✅ Model loaded successfully!")
    print(f"   📍 Device: {model.device}")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    exit(1)

# Test 2: Create a fake frame with a "person" (just to test inference)
print("\n2️⃣  Testing Detection Pipeline...")
try:
    # Create a dummy 640x480 BGR image
    fake_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    # Run detection (will probably find nothing, but tests the pipeline)
    people = detect_people(model, fake_frame, conf_thres=0.3)
    
    print(f"   ✅ Detection ran successfully!")
    print(f"   📊 Detections found: {len(people)}")
    print(f"   ℹ️  (Random image, so 0 detections is expected)")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    exit(1)

# Test 3: OpenCV availability
print("\n3️⃣  Testing OpenCV Video Capabilities...")
try:
    print(f"   OpenCV version: {cv2.__version__}")
    print(f"   ✅ OpenCV loaded successfully!")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    exit(1)

print("\n" + "="*60)
print("✅ ALL TESTS PASSED!")
print("="*60)
print("\n📋 Summary:")
print("   • YOLOv8 model: WORKING")
print("   • Detection pipeline: WORKING")
print("   • OpenCV: WORKING")
print("\n💡 Next steps:")
print("   • To test with a video file: python test_detection.py --source /path/to/video.mp4")
print("   • To test with RTSP: python test_detection.py --source rtsp://url --mode rtsp")
print("   • For now, the core AI is confirmed working!")
print("="*60 + "\n")

