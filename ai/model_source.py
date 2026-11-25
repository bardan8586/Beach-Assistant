"""Decide which YOLO weights the worker loads.

Order, first match wins:

1. ``MODEL_URL`` — download that file into the model cache.
2. ``HF_MODEL_REPO`` — download ``HF_MODEL_FILENAME`` (default ``best.pt``)
   from a Hugging Face model repo. A private repo needs ``HF_TOKEN``.
3. ``MODEL_NAME`` — a bare Ultralytics name such as ``yolov8n.pt``, or a path
   that exists on disk.
4. The fine-tuned ``best.pt`` checked in under the training run, when that
   file is actually present.
5. ``yolov8n.pt`` for the PyTorch backend, or ``ai/models/yolov8n.onnx``
   when ``INFERENCE_BACKEND=onnx``. The ONNX file is the COCO nano model.
   It only knows person, not the beach labels. Set ``MODEL_URL`` to a
   custom ``.onnx`` file to override it. The PyTorch fallback is downloaded
   by Ultralytics on first use.

A ``MODEL_NAME`` that points at a missing file does not crash startup. The
worker logs the miss and uses ``yolov8n.pt``.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

AI_DIR = Path(__file__).resolve().parent
BUNDLED_BEST = (
    AI_DIR
    / "runs"
    / "detect"
    / "runs-mai600"
    / "roboflow_v2_yolov8n_e5"
    / "weights"
    / "best.pt"
)
BUNDLED_ONNX = AI_DIR / "models" / "yolov8n.onnx"
FALLBACK_MODEL = "yolov8n.pt"
FALLBACK_ONNX = "yolov8n.onnx"


def resolve_model_path() -> str:
    model_url = os.getenv("MODEL_URL", "").strip()
    if model_url:
        destination = _cache_dir() / _filename_from_url(model_url)
        _download(model_url, destination)
        print(f"Model weights from MODEL_URL -> {destination}")
        return str(destination)

    repo = os.getenv("HF_MODEL_REPO", "").strip()
    if repo:
        filename = os.getenv("HF_MODEL_FILENAME", "best.pt").strip() or "best.pt"
        path = _download_hub(repo, filename)
        print(f"Model weights from HF_MODEL_REPO {repo} -> {path}")
        return path

    if _onnx_mode():
        return _resolve_onnx_file()

    explicit = os.getenv("MODEL_NAME", "").strip()
    if explicit:
        resolved = _explicit_model(explicit)
        if resolved:
            return resolved

    if BUNDLED_BEST.is_file():
        print(f"Using fine-tuned weights at {BUNDLED_BEST}")
        return str(BUNDLED_BEST)

    print(
        "best.pt is not in this checkout. "
        f"Using {FALLBACK_MODEL} (COCO person). "
        "Set MODEL_URL or HF_MODEL_REPO to load beach weights."
    )
    return FALLBACK_MODEL


def _onnx_mode() -> bool:
    return os.getenv("INFERENCE_BACKEND", "auto").strip().lower() == "onnx"


def _resolve_onnx_file() -> str:
    explicit = os.getenv("MODEL_NAME", "").strip()
    if explicit:
        path = Path(explicit)
        if path.is_file() and path.suffix.lower() == ".onnx":
            return str(path.resolve())
        bundled_name = AI_DIR / "models" / Path(explicit).name
        if explicit.lower().endswith(".onnx") and bundled_name.is_file():
            return str(bundled_name.resolve())
        if not explicit.lower().endswith(".onnx"):
            print(f"INFERENCE_BACKEND=onnx ignores non-ONNX MODEL_NAME={explicit}")
    if BUNDLED_ONNX.is_file():
        print(f"Using bundled ONNX weights at {BUNDLED_ONNX}")
        return str(BUNDLED_ONNX)
    print(
        f"{BUNDLED_ONNX} is missing. "
        "Set MODEL_URL to an .onnx file, or export yolov8n.onnx into ai/models/."
    )
    return str(BUNDLED_ONNX)


def _cache_dir() -> Path:
    configured = os.getenv("MODEL_CACHE_DIR", "").strip()
    path = Path(configured) if configured else AI_DIR / "models" / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _explicit_model(explicit: str) -> str | None:
    path = Path(explicit)
    if path.is_file():
        return str(path.resolve())
    # Bare checkpoint names are downloaded by Ultralytics. A path that is
    # not on disk is a missing best.pt, not a request to fail the process.
    if "/" not in explicit and "\\" not in explicit and explicit.endswith((".pt", ".onnx")):
        return explicit
    print(f"MODEL_NAME={explicit} is not a file. Falling back to {FALLBACK_MODEL}.")
    return FALLBACK_MODEL


def _filename_from_url(url: str) -> str:
    name = Path(urlparse(url).path).name
    if name and name not in {".", "/"}:
        return name
    return "weights.pt"


def _download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and destination.stat().st_size > 0:
        return
    temporary = destination.with_suffix(destination.suffix + ".partial")
    with urlopen(url, timeout=120) as response, temporary.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
    temporary.replace(destination)


def _download_hub(repo: str, filename: str) -> str:
    try:
        from huggingface_hub import hf_hub_download
    except ImportError as exc:
        raise RuntimeError(
            "HF_MODEL_REPO is set but huggingface_hub is not installed. "
            "pip install huggingface_hub"
        ) from exc
    token = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN") or None
    return hf_hub_download(repo_id=repo, filename=filename, token=token)
