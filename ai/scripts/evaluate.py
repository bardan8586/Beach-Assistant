#!/usr/bin/env python3
"""Reproducible detection evaluation.

With weights and a YOLO dataset this runs Ultralytics validation (mAP,
per-class metrics, confusion matrix saved by Ultralytics) and writes a
markdown report. Without them it still runs the local matcher on a built-in
fixture so the metric code can be checked, and it says clearly that dataset
mAP was not measured.

Usage:

    python ai/scripts/evaluate.py
    python ai/scripts/evaluate.py --weights path/to/best.pt --data path/to/data.yaml
    python ai/scripts/evaluate.py --benchmark
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from classes import CANONICAL_CLASSES  # noqa: E402
from metrics import confusion_matrix, micro_scores, per_class_scores  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "docs" / "evaluation"


def fixture_images() -> list[dict]:
    """Tiny hand-built set used when the Roboflow files are not on disk.

    This is a unit fixture, not a beach validation result.
    """
    box = (10, 10, 50, 80)
    shifted = (12, 12, 52, 82)
    other = (200, 200, 240, 280)
    return [
        {
            "gt": [{"cls": "drowning", "box": box}, {"cls": "swimming", "box": other}],
            "pred": [
                {"cls": "drowning", "box": shifted, "conf": 0.9},
                {"cls": "swimming", "box": other, "conf": 0.8},
            ],
        },
        {
            "gt": [{"cls": "person", "box": box}],
            "pred": [{"cls": "swimming", "box": shifted, "conf": 0.6}],
        },
        {
            "gt": [{"cls": "out_of_water", "box": box}],
            "pred": [],
        },
    ]


def render_matrix(matrix: list[list[int]], labels: list[str]) -> str:
    header = "| | " + " | ".join(labels) + " | background |"
    rule = "|---|" + "|".join(["---:"] * (len(labels) + 1)) + "|"
    rows = [header, rule]
    names = list(labels) + ["background"]
    for name, row in zip(names, matrix):
        rows.append("| " + name + " | " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(rows)


def render_scores(scores: list[dict]) -> str:
    lines = [
        "| Class | Precision | Recall | F1 | Support | TP | FP | FN |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in scores:
        lines.append(
            "| {class} | {precision:.3f} | {recall:.3f} | {f1:.3f} | {support} | {tp} | {fp} | {fn} |".format(
                **row
            )
        )
    return "\n".join(lines)


def evaluate_fixture() -> dict:
    labels = list(CANONICAL_CLASSES)
    matrix = confusion_matrix(fixture_images(), labels, iou_threshold=0.5)
    scores = per_class_scores(matrix, labels)
    return {"labels": labels, "matrix": matrix, "per_class": scores, "micro": micro_scores(scores)}


def try_ultralytics_val(weights: Path, data: Path, imgsz: int, device: str | None) -> dict | None:
    try:
        from ultralytics import YOLO
    except ImportError:
        return {"error": "ultralytics is not installed"}
    model = YOLO(str(weights))
    metrics = model.val(data=str(data), imgsz=imgsz, device=device or "cpu", plots=True, split="val")
    names = getattr(metrics, "names", {})
    if isinstance(names, dict):
        ordered = [names[i] for i in sorted(names)]
    else:
        ordered = list(names)
    box = metrics.box
    per_class = []
    # Ultralytics exposes per-class vectors when more than one class is present.
    precisions = list(getattr(box, "p", []) or [])
    recalls = list(getattr(box, "r", []) or [])
    maps = list(getattr(box, "ap50", []) or [])
    for index, name in enumerate(ordered):
        per_class.append(
            {
                "class": name,
                "precision": float(precisions[index]) if index < len(precisions) else None,
                "recall": float(recalls[index]) if index < len(recalls) else None,
                "map50": float(maps[index]) if index < len(maps) else None,
            }
        )
    return {
        "precision": float(box.mp),
        "recall": float(box.mr),
        "map50": float(box.map50),
        "map50_95": float(box.map),
        "per_class": per_class,
        "save_dir": str(getattr(metrics, "save_dir", "")),
    }


def write_report(path: Path, fixture: dict, ultralytics_result: dict | None, notes: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Detection evaluation",
        "",
        f"Generated {now} by `ai/scripts/evaluate.py`.",
        "",
        "## What was measured this run",
        "",
    ]
    if ultralytics_result and "map50" in ultralytics_result:
        lines += [
            "Ultralytics validation ran on the weights and data passed to this script.",
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| Precision | {ultralytics_result['precision']:.4f} |",
            f"| Recall | {ultralytics_result['recall']:.4f} |",
            f"| mAP50 | {ultralytics_result['map50']:.4f} |",
            f"| mAP50-95 | {ultralytics_result['map50_95']:.4f} |",
            "",
            "Per-class (Ultralytics):",
            "",
            "| Class | Precision | Recall | mAP50 |",
            "|---|---:|---:|---:|",
        ]
        for row in ultralytics_result["per_class"]:
            def fmt(value):
                return "n/a" if value is None else f"{value:.4f}"

            lines.append(
                f"| {row['class']} | {fmt(row['precision'])} | {fmt(row['recall'])} | {fmt(row['map50'])} |"
            )
        lines += ["", f"Ultralytics plots: `{ultralytics_result.get('save_dir')}`", ""]
    else:
        lines += [
            "Dataset mAP was **not** measured. The fine-tuned `best.pt` weights and the Roboflow images are gitignored and were not present for this run.",
            "",
            "Previously recorded validation numbers (5 epochs, CPU, 7 duplicate class names, from the project report and `args.yaml`, not remeasured here):",
            "",
            "| Metric | Recorded value |",
            "|---|---:|",
            "| Precision | 0.642 |",
            "| Recall | 0.572 |",
            "| mAP50 | 0.614 |",
            "| mAP50-95 | 0.321 |",
            "",
        ]
        if ultralytics_result and ultralytics_result.get("error"):
            lines.append(f"Ultralytics note: {ultralytics_result['error']}")
            lines.append("")
    lines += [
        "## Local matcher fixture",
        "",
        "The table below is the built-in fixture inside `evaluate.py`. It checks the confusion-matrix code. It is not beach-model accuracy.",
        "",
        render_scores(fixture["per_class"]),
        "",
        render_matrix(fixture["matrix"], fixture["labels"]),
        "",
        f"Fixture micro precision {fixture['micro']['precision']:.3f}, recall {fixture['micro']['recall']:.3f}.",
        "",
        "## Notes",
        "",
    ]
    for note in notes:
        lines.append(f"- {note}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, default=None)
    parser.add_argument("--data", type=Path, default=None)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default=None)
    parser.add_argument("--benchmark", action="store_true", help="Also run the CPU latency benchmark")
    parser.add_argument("--report", type=Path, default=REPORT_DIR / "evaluation.md")
    args = parser.parse_args()

    notes = [
        "Canonical classes are drowning, out_of_water, swimming, person. Duplicate Roboflow names should be remapped with `ai/scripts/prepare_dataset.py` before a new training run.",
        "IoU threshold for the local matcher is 0.5.",
    ]
    ultralytics_result = None
    if args.weights and args.data:
        if not args.weights.is_file() or not args.data.is_file():
            print("error: --weights and --data must both exist", file=sys.stderr)
            return 1
        print(f"Running Ultralytics val on {args.weights}")
        ultralytics_result = try_ultralytics_val(args.weights, args.data, args.imgsz, args.device)
    elif args.weights or args.data:
        print("error: pass both --weights and --data", file=sys.stderr)
        return 1
    else:
        notes.append("No --weights/--data flags, so Ultralytics validation was skipped.")

    fixture = evaluate_fixture()
    write_report(args.report, fixture, ultralytics_result, notes)
    (REPORT_DIR / "fixture_metrics.json").write_text(json.dumps(fixture, indent=2), encoding="utf-8")
    print(f"Wrote {args.report}")

    if args.benchmark:
        import runpy

        bench_path = Path(__file__).resolve().parent / "benchmark_inference.py"
        sys.argv = [str(bench_path)]
        runpy.run_path(str(bench_path), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
