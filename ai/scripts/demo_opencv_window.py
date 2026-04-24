#!/usr/bin/env python3
"""
Minimal OpenCV window demo — same file you'd point the app at, local only.

Usage (from repo root or anywhere):
  python ai/scripts/demo_opencv_window.py /path/to/video.mp4
  python ai/scripts/demo_opencv_window.py 0          # webcam index 0

Press Q or Esc to quit. No backend, no torch — OpenCV only.
"""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenCV window video demo")
    parser.add_argument(
        "source",
        nargs="?",
        default=None,
        help="Video file path, or a single digit for webcam (e.g. 0)",
    )
    args = parser.parse_args()

    try:
        import cv2
    except ImportError:
        print("OpenCV is not installed. Run: pip install opencv-python", file=sys.stderr)
        return 1

    src = args.source
    if src is None:
        print("Usage: python demo_opencv_window.py <video.mp4 | 0>", file=sys.stderr)
        return 2

    cap_src: str | int
    if len(src) == 1 and src.isdigit():
        cap_src = int(src)
    else:
        cap_src = src

    cap = cv2.VideoCapture(cap_src)
    if not cap.isOpened():
        print(f"Could not open: {src}", file=sys.stderr)
        return 1

    win = "Beach Assistant — OpenCV demo"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    frame_i = 0
    print("Window opened. Press Q or Esc to quit.")

    while True:
        ok, frame = cap.read()
        if not ok:
            print("End of stream.")
            break
        frame_i += 1
        cv2.putText(
            frame,
            f"Beach Assistant demo | frame {frame_i} | Q=quit",
            (12, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 220, 255),
            2,
            cv2.LINE_AA,
        )
        cv2.imshow(win, frame)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), ord("Q"), 27):
            break

    cap.release()
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
