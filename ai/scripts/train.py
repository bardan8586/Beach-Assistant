#!/usr/bin/env python3
"""Fine-tune YOLOv8n on the 4-class beach dataset.

The recorded run trained the 7-name duplicate label set for 5 epochs on CPU
(see ``ai/runs/detect/runs-mai600/roboflow_v2_yolov8n_e5/args.yaml``).
Warmup was 3 of those 5 epochs and the duplicate names split one concept
across two class ids. This script remaps labels first, then trains with a
fine-tune learning rate and cosine schedule sized for a longer run.

It does not download weights or data. Point ``--data`` at a prepared yaml
or let ``--prepare`` build one from the Roboflow download.

Examples:

    # GPU, 50 epochs (the run this script is set up for)
    python ai/scripts/train.py --device 0 --epochs 50 --batch 16

    # CPU smoke (expect it to be slow; do not treat a few epochs as a result)
    python ai/scripts/train.py --device cpu --epochs 1 --batch 4 --fraction 0.05
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from prepare_dataset import prepare_dataset  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    ai_dir = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=None, help="Ultralytics data.yaml")
    parser.add_argument("--prepare", action="store_true", help="Remap the Roboflow set before training")
    parser.add_argument("--src", type=Path, default=ai_dir / "datasets" / "roboflow-drowning")
    parser.add_argument("--dst", type=Path, default=ai_dir / "datasets" / "roboflow-drowning-4cls")
    parser.add_argument("--model", default="yolov8n.pt")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default=None, help="cpu, 0, or leave unset to auto-select")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--fraction", type=float, default=1.0, help="Fraction of training images")
    parser.add_argument("--project", default=str(ai_dir / "runs" / "detect"))
    parser.add_argument("--name", default="roboflow_4cls_yolov8n")
    parser.add_argument("--seed", type=int, default=0)
    return parser


def train_kwargs(args: argparse.Namespace, data_yaml: Path) -> dict:
    """Hyperparameters for a real fine-tune, not the 5-epoch warmup-heavy run."""
    return {
        "data": str(data_yaml),
        "epochs": args.epochs,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "device": args.device,
        "workers": args.workers,
        "fraction": args.fraction,
        "patience": 20,
        "pretrained": True,
        "optimizer": "AdamW",
        # Lower than the recorded lr0=0.01. That run spent 3 of 5 epochs in warmup.
        "lr0": 0.002,
        "lrf": 0.01,
        "warmup_epochs": 1.0 if args.epochs < 10 else 3.0,
        "cos_lr": True,
        "close_mosaic": 10 if args.epochs >= 20 else max(1, args.epochs // 5),
        "hsv_h": 0.015,
        "hsv_s": 0.7,
        "hsv_v": 0.4,
        "degrees": 5.0,
        "translate": 0.1,
        "scale": 0.6,
        "shear": 0.0,
        "perspective": 0.0,
        "flipud": 0.0,
        "fliplr": 0.5,
        "mosaic": 1.0,
        "mixup": 0.05,
        "copy_paste": 0.1,
        "erasing": 0.3,
        "seed": args.seed,
        "deterministic": True,
        "plots": True,
        "project": args.project,
        "name": args.name,
        "exist_ok": True,
    }


def main() -> int:
    args = build_parser().parse_args()
    if args.prepare or args.data is None:
        try:
            data_yaml = prepare_dataset(args.src, args.dst)
        except (FileNotFoundError, ValueError, KeyError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
    else:
        data_yaml = args.data
    if not data_yaml.is_file():
        print(f"error: data yaml not found: {data_yaml}", file=sys.stderr)
        return 1
    try:
        from ultralytics import YOLO
    except ImportError:
        print("error: ultralytics is not installed. pip install -r ai/requirements.txt", file=sys.stderr)
        return 1
    if args.device is None:
        try:
            import torch

            args.device = "0" if torch.cuda.is_available() else "cpu"
        except ImportError:
            args.device = "cpu"
    print(f"Training {args.model} on {data_yaml} for {args.epochs} epochs ({args.device})")
    model = YOLO(args.model)
    model.train(**train_kwargs(args, data_yaml))
    print("Training finished. Best weights are under the run's weights/best.pt")
    print("Set MODEL_NAME to that path before starting the API.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
