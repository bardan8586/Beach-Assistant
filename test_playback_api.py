#!/usr/bin/env python3
"""
Test script for Task 1.3 - Playback API Endpoints
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000/api"

print("🧪 Testing Playback API Endpoints (Task 1.3)")
print("=" * 60)

# Use existing video from uploads
video_id = "realtime"  # The AI sends data with video_id="realtime"

print(f"\n1️⃣ Testing GET /api/video/{video_id}/metadata")
try:
    response = requests.get(f"{BASE_URL}/video/{video_id}/metadata", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Metadata retrieved: {data.get('metadata', {}).get('filename', 'N/A')}")
        print(f"   Dimensions: {data.get('metadata', {}).get('width')}x{data.get('metadata', {}).get('height')}")
    elif response.status_code == 404:
        print(f"⚠️  Metadata not found (404) - This is expected if video wasn't uploaded via /upload")
        print(f"   Note: 'realtime' video_id is used during live processing")
    else:
        print(f"❌ Unexpected status: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

print(f"\n2️⃣ Testing GET /api/video/{video_id}/results")
try:
    response = requests.get(f"{BASE_URL}/video/{video_id}/results", timeout=5)
    if response.status_code == 200:
        data = response.json()
        frame_count = data.get('frame_count', 0)
        print(f"✅ Results retrieved: {frame_count} frames")
        
        if frame_count > 0:
            first_frame = data['results'][0]
            last_frame = data['results'][-1]
            print(f"   First frame: index={first_frame.get('frame_index')}, timestamp={first_frame.get('timestamp_ms')}ms")
            print(f"   Last frame: index={last_frame.get('frame_index')}, timestamp={last_frame.get('timestamp_ms')}ms")
            print(f"   Video dimensions: {first_frame.get('video_width')}x{first_frame.get('video_height')}")
            print(f"   Swimmers in first frame: {len(first_frame.get('swimmers', []))}")
    elif response.status_code == 404:
        print(f"⚠️  No results found (404) - Video needs to be processed first")
        print(f"   Run: SEND_TO_BACKEND=true python ai/main.py tests/data/Video_Generation_of_Beach_Swimming.mp4")
    else:
        print(f"❌ Unexpected status: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

print(f"\n3️⃣ Testing GET /api/video/{video_id}/results with time range")
try:
    # Request frames between 5-10 seconds (5000-10000 ms)
    response = requests.get(
        f"{BASE_URL}/video/{video_id}/results",
        params={"from_ms": 5000, "to_ms": 10000},
        timeout=5
    )
    if response.status_code == 200:
        data = response.json()
        frame_count = data.get('frame_count', 0)
        print(f"✅ Range results [5000-10000ms]: {frame_count} frames")
        
        if frame_count > 0:
            first_frame = data['results'][0]
            last_frame = data['results'][-1]
            print(f"   First frame timestamp: {first_frame.get('timestamp_ms')}ms")
            print(f"   Last frame timestamp: {last_frame.get('timestamp_ms')}ms")
    elif response.status_code == 404:
        print(f"⚠️  No results found (404)")
    else:
        print(f"❌ Unexpected status: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("📊 Test Complete")
print("\n💡 To generate test data:")
print("   cd ai")
print("   SYSTEM_MODE=playback SEND_TO_BACKEND=true python main.py ../tests/data/Video_Generation_of_Beach_Swimming.mp4")
