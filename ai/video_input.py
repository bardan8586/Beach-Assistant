import cv2
import threading
import time

class RTSPVideoStream:
    """
    Connects to an RTSP camera and yields frames at the desired output_fps.
    Handles automatic reconnects and provides thread-safe frame access.
    """
    def __init__(self, rtsp_url, output_fps=10, reconnect_interval=5, max_retries=0):
        """
        :param rtsp_url: str, the RTSP stream URL
        :param output_fps: float, frame sampling rate for consumers
        :param reconnect_interval: seconds between reconnect attempts on failure
        :param max_retries: max reconnect attempts (0=infinite)
        """
        self.rtsp_url = rtsp_url
        self.output_fps = output_fps
        self.reconnect_interval = reconnect_interval
        self.max_retries = max_retries

        self._capture = None
        self._latest_frame = None
        self._frame_time = 0  # timestamp of the latest frame
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def _open_capture(self):
        # Use GStreamer or OpenCV backend optimized for RTSP
        cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            return None
        return cap

    def _capture_loop(self):
        retries = 0
        target_interval = 1.0 / self.output_fps
        while not self._stop.is_set():
            if self._capture is None or not self._capture.isOpened():
                self._capture = self._open_capture()
                if self._capture is None:
                    retries += 1
                    if 0 < self.max_retries <= retries:
                        break
                    time.sleep(self.reconnect_interval)
                    continue
                retries = 0  # Reset on successful connection

            grabbed, frame = self._capture.read()
            if not grabbed or frame is None:
                # Sleep briefly to avoid busy loop on failure
                time.sleep(self.reconnect_interval)
                # Try to reopen connection on next loop
                self._capture.release()
                self._capture = None
                continue

            now = time.time()
            # Only update frame at output_fps (dropping excess frames ASAP)
            if now - self._frame_time >= target_interval:
                with self._lock:
                    self._latest_frame = frame
                    self._frame_time = now
            else:
                # Drop this frame, don't block
                pass

            # Tight loop, but yield control so we don't busy-wait
            time.sleep(max(0, target_interval - (time.time() - now)))

        if self._capture is not None:
            self._capture.release()

    def read(self, timeout=1.0):
        """
        Returns the most recent frame and its timestamp.
        Returns (frame, timestamp); frame is None if not yet available.
        Thread-safe.
        """
        start = time.time()
        while time.time() - start < timeout:
            with self._lock:
                if self._latest_frame is not None:
                    # Return a copy to avoid race on buffer
                    return self._latest_frame.copy(), self._frame_time
            time.sleep(0.01)
        return None, None

    def stop(self):
        """Stops the capture thread and releases resources."""
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=2)
        if self._capture is not None:
            self._capture.release()

    def is_running(self):
        """Return True if the capture thread is active."""
        return self._thread.is_alive() and not self._stop.is_set()

    def __del__(self):
        self.stop()

# Usage Example (downstream consumer):
# cam = RTSPVideoStream("rtsp://user:pw@ip/...")
# while True:
#     frame, ts = cam.read()
#     if frame is not None:
#         process(frame)
#     else:
#         time.sleep(0.05)
# cam.stop()

