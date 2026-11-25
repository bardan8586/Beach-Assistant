"""Model path selection when best.pt is not in the checkout."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ai"))
sys.path.insert(0, str(ROOT / "backend"))

from model_source import FALLBACK_MODEL, resolve_model_path  # noqa: E402
from app.config import settings  # noqa: E402

VERCEL_ORIGIN = "https://beach-assistant-preview.vercel.app"


def test_missing_best_pt_uses_yolov8n(monkeypatch):
    monkeypatch.delenv("MODEL_URL", raising=False)
    monkeypatch.delenv("HF_MODEL_REPO", raising=False)
    monkeypatch.delenv("MODEL_NAME", raising=False)
    monkeypatch.delenv("INFERENCE_BACKEND", raising=False)
    assert resolve_model_path() == FALLBACK_MODEL


def test_missing_model_path_does_not_crash(monkeypatch):
    monkeypatch.delenv("MODEL_URL", raising=False)
    monkeypatch.delenv("HF_MODEL_REPO", raising=False)
    monkeypatch.delenv("INFERENCE_BACKEND", raising=False)
    monkeypatch.setenv("MODEL_NAME", "/no/such/best.pt")
    assert resolve_model_path() == FALLBACK_MODEL


def test_bare_checkpoint_name_is_kept(monkeypatch):
    monkeypatch.delenv("MODEL_URL", raising=False)
    monkeypatch.delenv("HF_MODEL_REPO", raising=False)
    monkeypatch.setenv("MODEL_NAME", "yolov8n.pt")
    assert resolve_model_path() == "yolov8n.pt"


def test_model_url_downloads_once(monkeypatch, tmp_path):
    payload = b"not-a-real-weight-file"
    monkeypatch.setenv("MODEL_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv("HF_MODEL_REPO", raising=False)
    monkeypatch.delenv("MODEL_NAME", raising=False)

    def fake_download(url, destination: Path):
        assert url == "https://example.test/beach/best.pt"
        destination.write_bytes(payload)

    monkeypatch.setattr("model_source._download", fake_download)
    monkeypatch.setenv("MODEL_URL", "https://example.test/beach/best.pt")
    path = Path(resolve_model_path())
    assert path.name == "best.pt"
    assert path.read_bytes() == payload


def test_default_cors_includes_vercel_preview():
    assert VERCEL_ORIGIN in settings.ALLOWED_ORIGINS


def test_onnx_backend_selects_bundled_file(monkeypatch):
    monkeypatch.setenv("INFERENCE_BACKEND", "onnx")
    monkeypatch.delenv("MODEL_URL", raising=False)
    monkeypatch.delenv("HF_MODEL_REPO", raising=False)
    monkeypatch.delenv("MODEL_NAME", raising=False)
    assert resolve_model_path().endswith("yolov8n.onnx")


def test_nms_keeps_the_higher_score():
    sys.path.insert(0, str(ROOT / "ai"))
    import numpy as np
    from onnx_yolo import nms_indices

    boxes = np.array([[0, 0, 10, 10], [1, 1, 11, 11], [50, 50, 70, 70]], dtype=np.float32)
    scores = np.array([0.4, 0.9, 0.8], dtype=np.float32)
    kept = nms_indices(boxes, scores, 0.5)
    assert 1 in kept
    assert 0 not in kept
    assert 2 in kept


def test_space_bundle_keeps_docker_front_matter(tmp_path):
    sys.path.insert(0, str(ROOT / "deploy" / "huggingface"))
    from sync_space import stage_space

    stage_space(tmp_path)
    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "sdk: docker" in readme
    assert "app_port: 7860" in readme
    assert "suggested_hardware: cpu-basic" in readme
    dockerfile = (tmp_path / "Dockerfile").read_text(encoding="utf-8")
    assert "7860" in dockerfile
    assert (tmp_path / "backend" / "app" / "main.py").is_file()
    assert (tmp_path / "ai" / "model_source.py").is_file()
    assert not (tmp_path / "ai" / "runs").exists()
