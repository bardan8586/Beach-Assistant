"""ONNX preflight must not require torch."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.utils.ai_runtime import required_ai_modules  # noqa: E402


def test_onnx_preflight_skips_torch(monkeypatch):
    monkeypatch.setenv("INFERENCE_BACKEND", "onnx")
    modules = required_ai_modules()
    assert "onnxruntime" in modules
    assert "torch" not in modules
    assert "ultralytics" not in modules


def test_default_preflight_still_uses_torch(monkeypatch):
    monkeypatch.delenv("INFERENCE_BACKEND", raising=False)
    modules = required_ai_modules()
    assert modules == ["cv2", "torch", "ultralytics"]
