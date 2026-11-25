#!/usr/bin/env python3
"""Measure detector latency on this machine.

The fine-tuned beach weights are not in the repository, so this times
YOLOv8n (the same architecture as the recorded training run) loaded from
the Ultralytics checkpoint name ``yolov8n.pt``. Numbers are for that
checkpoint, not for ``best.pt``.

The historical upload path also called ``cv2.waitKey(100)`` on every
processed frame even when no window was open (``OUTPUT_FPS`` defaults to
10). The benchmark reports model time and the same time plus that 100 ms
pause so the pacing bug is visible.

Usage:

    python ai/scripts/benchmark_inference.py
    python ai/scripts/benchmark_inference.py --frames 20 --imgsz 640 416
"""

from __future__ import annotations

import argparse
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "docs" / "evaluation" / "benchmark.md"
JSON_OUT = ROOT / "docs" / "evaluation" / "benchmark.json"


def _sync(device: str) -> None:
    if device.startswith("cuda"):
        import torch

        torch.cuda.synchronize()


def time_predict(model, frames: list[np.ndarray], imgsz: int, device: str) -> dict:
    # Warmup. The first call loads kernels and is not a steady-state sample.
    model.predict(frames[0], imgsz=imgsz, device=device, verbose=False)
    _sync(device)
    started = time.perf_counter()
    for frame in frames:
        model.predict(frame, imgsz=imgsz, device=device, verbose=False)
    _sync(device)
    elapsed = time.perf_counter() - started
    per_frame = elapsed / len(frames)
    return {
        "imgsz": imgsz,
        "frames": len(frames),
        "seconds": elapsed,
        "ms_per_frame": per_frame * 1000.0,
        "fps": (1.0 / per_frame) if per_frame else 0.0,
        "fps_with_legacy_100ms_wait": (1.0 / (per_frame + 0.1)) if per_frame else 0.0,
    }


def time_batch(model, frames: list[np.ndarray], imgsz: int, device: str, batch: int) -> dict:
    model.predict(frames[:batch], imgsz=imgsz, device=device, verbose=False)
    _sync(device)
    chunks = [frames[i : i + batch] for i in range(0, len(frames), batch)]
    started = time.perf_counter()
    for chunk in chunks:
        model.predict(chunk, imgsz=imgsz, device=device, verbose=False)
    _sync(device)
    elapsed = time.perf_counter() - started
    per_frame = elapsed / len(frames)
    return {
        "imgsz": imgsz,
        "batch": batch,
        "frames": len(frames),
        "seconds": elapsed,
        "ms_per_frame": per_frame * 1000.0,
        "fps": (1.0 / per_frame) if per_frame else 0.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="yolov8n.pt")
    parser.add_argument("--frames", type=int, default=12)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--imgsz", type=int, nargs="+", default=[640, 480, 416])
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--device", default=None)
    parser.add_argument("--onnx", action="store_true", help="Also export ONNX and time that file")
    args = parser.parse_args()

    import torch
    from ultralytics import YOLO

    device = args.device or ("cuda:0" if torch.cuda.is_available() else "cpu")
    model = YOLO(args.model)
    rng = np.random.default_rng(0)
    frames = [
        rng.integers(0, 255, size=(args.height, args.width, 3), dtype=np.uint8) for _ in range(args.frames)
    ]
    single = [time_predict(model, frames, size, device) for size in args.imgsz]
    batched = time_batch(model, frames, args.imgsz[0], device, args.batch)
    onnx_row = None
    if args.onnx:
        exported = Path(model.export(format="onnx", imgsz=args.imgsz[0]))
        onnx_model = YOLO(str(exported))
        onnx_row = time_predict(onnx_model, frames, args.imgsz[0], device)
        onnx_row["file"] = str(exported)

    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "model": args.model,
        "device": device,
        "torch": torch.__version__,
        "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
        "frame_shape": [args.height, args.width, 3],
        "note": (
            "YOLOv8n public checkpoint, not the fine-tuned beach weights. "
            "Random frames, so this is latency only, not accuracy."
        ),
        "single": single,
        "batch": batched,
        "onnx": onnx_row,
        "legacy_wait_ms": 100,
    }
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Inference latency",
        "",
        f"Generated {payload['generated_at']} by `ai/scripts/benchmark_inference.py`.",
        "",
        payload["note"],
        "",
        f"- Model: `{payload['model']}`",
        f"- Device: `{payload['device']}`",
        f"- Torch: `{payload['torch']}`",
        f"- Machine: `{payload['platform']}`",
        f"- Frame: {args.width}x{args.height} random uint8, {args.frames} timed frames after one warmup",
        "",
        "## One frame at a time",
        "",
        "| imgsz | ms/frame | FPS | FPS if the old 100 ms waitKey is added |",
        "|---:|---:|---:|---:|",
    ]
    for row in single:
        lines.append(
            f"| {row['imgsz']} | {row['ms_per_frame']:.1f} | {row['fps']:.2f} | {row['fps_with_legacy_100ms_wait']:.2f} |"
        )
    lines += [
        "",
        "## Batched predict",
        "",
        f"Batch {batched['batch']} at imgsz {batched['imgsz']}: "
        f"{batched['ms_per_frame']:.1f} ms/frame ({batched['fps']:.2f} FPS).",
        "",
    ]
    if onnx_row:
        lines += [
            "## ONNX",
            "",
            f"Exported `{onnx_row['file']}` and timed imgsz {onnx_row['imgsz']}: "
            f"{onnx_row['ms_per_frame']:.1f} ms/frame ({onnx_row['fps']:.2f} FPS) "
            f"against {single[0]['ms_per_frame']:.1f} ms/frame for the PyTorch checkpoint at the same size.",
            "",
        ]
    lines += [
        "The upload pipeline now skips `cv2.waitKey` unless `SHOW_WINDOW=true`, posts ingest off the frame loop, and leaves pose estimation off unless `ENABLE_POSE=true`. Those changes are not all inside the millisecond column above. The last column is the model time plus the 100 ms pause the old loop added on every processed frame.",
        "",
        (
            "Half precision needs CUDA and was not timed on this CPU."
            if device == "cpu"
            else "Half precision is used when HALF_PRECISION is auto or true on CUDA."
        ),
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {REPORT}")
    for row in single:
        print(
            f"imgsz {row['imgsz']}: {row['ms_per_frame']:.1f} ms  {row['fps']:.2f} FPS  "
            f"(with 100ms wait {row['fps_with_legacy_100ms_wait']:.2f} FPS)"
        )
    print(
        f"batch {batched['batch']} imgsz {batched['imgsz']}: "
        f"{batched['ms_per_frame']:.1f} ms/frame {batched['fps']:.2f} FPS"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
