"""Choose the AI interpreter checks without importing OpenCV or torch."""

from __future__ import annotations

import os


def required_ai_modules() -> list[str]:
    """Torch stays on the local/GPU path. The free Render image uses ONNX only."""
    backend = os.getenv("INFERENCE_BACKEND", "auto").strip().lower()
    if backend == "onnx":
        return ["cv2", "onnxruntime", "numpy", "norfair"]
    return ["cv2", "torch", "ultralytics"]
