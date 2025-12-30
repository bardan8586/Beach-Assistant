"""
Test script for video_input.py and detector.py
Tests RTSP ingestion and YOLOv8 person detection

Usage:
    python test_detection.py --source <video_file_or_rtsp_url>
"""

import cv2
import time
import argparse
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "ai"))

from video_input import RTSPVideoStream
from detector import load_yolov8_model, detect_people


def test_with_opencv_video(video_source: str, output_fps: int = 10):
    """
    Test detection pipeline with OpenCV video capture
    (simpler for local video files)
    """
    print(f"🎥 Loading video: {video_source}")
    cap = cv2.VideoCapture(video_source)
    
    if not cap.isOpened():
        print(f"❌ Failed to open video source: {video_source}")
        return
    
    print("🤖 Loading YOLOv8 model...")
    model = load_yolov8_model("yolov8n.pt")
    print(f"✅ Model loaded on device: {model.device}")
    
    frame_count = 0
    start_time = time.time()
    total_detections = 0
    
    print(f"\n▶️  Starting detection (press 'q' to quit)...")
    print("=" * 60)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("\n🏁 End of video reached")
            break
        
        frame_count += 1
        
        # Run detection
        people = detect_people(model, frame, conf_thres=0.3)
        total_detections += len(people)
        
        # Draw bounding boxes
        for (x1, y1, x2, y2, conf) in people:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"Person {conf:.2f}"
            cv2.putText(frame, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Add info overlay
        info_text = f"Frame: {frame_count} | People: {len(people)} | FPS: {frame_count / (time.time() - start_time):.1f}"
        cv2.putText(frame, info_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Display
        cv2.imshow('Beach Safety - Detection Test', frame)
        
        # Print status
        if frame_count % 30 == 0:
            elapsed = time.time() - start_time
            fps = frame_count / elapsed
            print(f"Frame {frame_count:4d} | People: {len(people):2d} | "
                  f"FPS: {fps:.1f} | Avg detections/frame: {total_detections/frame_count:.1f}")
        
        # Control frame rate
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\n⏹️  Stopped by user")
            break
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    
    # Summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Total frames processed: {frame_count}")
    print(f"Total time: {elapsed:.2f}s")
    print(f"Average FPS: {frame_count / elapsed:.1f}")
    print(f"Total people detected: {total_detections}")
    print(f"Average detections per frame: {total_detections / frame_count:.2f}")
    print("=" * 60)


def test_with_rtsp_stream(rtsp_url: str, output_fps: int = 10, duration: int = 30):
    """
    Test detection pipeline with RTSPVideoStream class
    (for actual RTSP cameras or network streams)
    """
    print(f"🎥 Connecting to RTSP stream: {rtsp_url}")
    print(f"   Output FPS: {output_fps}")
    
    stream = RTSPVideoStream(rtsp_url, output_fps=output_fps)
    
    print("🤖 Loading YOLOv8 model...")
    model = load_yolov8_model("yolov8n.pt")
    print(f"✅ Model loaded on device: {model.device}")
    
    # Wait for first frame
    print("⏳ Waiting for first frame...")
    frame, timestamp = stream.read(timeout=5.0)
    if frame is None:
        print("❌ Failed to get frame from stream")
        stream.stop()
        return
    
    print(f"✅ Stream connected! Frame shape: {frame.shape}")
    
    frame_count = 0
    start_time = time.time()
    total_detections = 0
    
    print(f"\n▶️  Starting detection for {duration}s (press 'q' to quit early)...")
    print("=" * 60)
    
    while time.time() - start_time < duration:
        frame, timestamp = stream.read(timeout=1.0)
        if frame is None:
            print("⚠️  No frame received, retrying...")
            time.sleep(0.1)
            continue
        
        frame_count += 1
        
        # Run detection
        people = detect_people(model, frame, conf_thres=0.3)
        total_detections += len(people)
        
        # Draw bounding boxes
        for (x1, y1, x2, y2, conf) in people:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"Person {conf:.2f}"
            cv2.putText(frame, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Add info overlay
        elapsed = time.time() - start_time
        info_text = f"Frame: {frame_count} | People: {len(people)} | FPS: {frame_count / elapsed:.1f}"
        cv2.putText(frame, info_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Display
        cv2.imshow('Beach Safety - RTSP Test', frame)
        
        # Print status
        if frame_count % 30 == 0:
            fps = frame_count / elapsed
            print(f"Frame {frame_count:4d} | People: {len(people):2d} | "
                  f"FPS: {fps:.1f} | Elapsed: {elapsed:.1f}s")
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\n⏹️  Stopped by user")
            break
    
    # Cleanup
    stream.stop()
    cv2.destroyAllWindows()
    
    # Summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Total frames processed: {frame_count}")
    print(f"Total time: {elapsed:.2f}s")
    print(f"Average FPS: {frame_count / elapsed:.1f}")
    print(f"Total people detected: {total_detections}")
    print(f"Average detections per frame: {total_detections / frame_count:.2f}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Test beach safety detection pipeline")
    parser.add_argument("--source", type=str, default="0",
                       help="Video source: file path, RTSP URL, or webcam index (0)")
    parser.add_argument("--fps", type=int, default=10,
                       help="Output frame rate (default: 10)")
    parser.add_argument("--duration", type=int, default=30,
                       help="Duration in seconds for RTSP streams (default: 30)")
    parser.add_argument("--mode", choices=["rtsp", "video"], default="video",
                       help="Mode: 'video' for files/webcam, 'rtsp' for RTSP streams")
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("🏖️  BEACH SAFETY AI - DETECTION PIPELINE TEST")
    print("=" * 60)
    print(f"Source: {args.source}")
    print(f"Mode: {args.mode}")
    print("=" * 60 + "\n")
    
    if args.mode == "rtsp":
        test_with_rtsp_stream(args.source, args.fps, args.duration)
    else:
        test_with_opencv_video(args.source, args.fps)


if __name__ == "__main__":
    main()

