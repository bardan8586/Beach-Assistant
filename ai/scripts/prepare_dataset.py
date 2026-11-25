#!/usr/bin/env python3
"""Collapse duplicate Roboflow class names and rewrite YOLO label ids.

The v2 drowning dataset ships seven names that are four concepts. This
script writes a sibling dataset whose ``data.yaml`` lists the canonical
classes and whose label files use the new indices. Images are symlinked,
not copied.

Usage (from repo root or ai/):

    python ai/scripts/prepare_dataset.py
    python ai/scripts/prepare_dataset.py --src ai/datasets/roboflow-drowning \\
        --dst ai/datasets/roboflow-drowning-4cls
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from classes import CANONICAL_ORDER, canonicalize_class  # noqa: E402


def parse_names(text: str) -> list[str]:
    """Parse the ``names`` field from an Ultralytics data.yaml file.

    Supports a flow list (``names: ['A', 'B']``) and a block list
    (``names:`` then ``- A``). Dict-style ``0: A`` lines are also accepted.
    """
    lines = text.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("names:"):
            continue
        rest = stripped[len("names:") :].strip()
        if rest.startswith("[") and rest.endswith("]"):
            inner = rest[1:-1]
            return [_unquote(part) for part in _split_flow(inner) if _unquote(part)]
        if rest:
            return [_unquote(part) for part in _split_flow(rest) if _unquote(part)]
        names: list[str] = []
        for follower in lines[index + 1 :]:
            item = follower.strip()
            if not item or item.startswith("#"):
                continue
            if item.startswith("- "):
                names.append(_unquote(item[2:].strip()))
                continue
            if ":" in item and not item.startswith(" ") is False:
                # "0: Drowning" or "  0: Drowning"
                left, right = item.split(":", 1)
                if left.strip().isdigit():
                    names.append(_unquote(right.strip()))
                    continue
            break
        return names
    raise ValueError("data.yaml has no names: field")


def _unquote(value: str) -> str:
    value = value.strip().strip(",")
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _split_flow(inner: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    quote: str | None = None
    for char in inner:
        if quote:
            if char == quote:
                quote = None
            else:
                current.append(char)
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char == ",":
            parts.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def remap_plan(names: list[str]) -> tuple[list[str], dict[int, int]]:
    """Return ``(new_names, old_index_to_new_index)``."""
    ordered: list[str] = []
    for canonical in CANONICAL_ORDER:
        if any(canonicalize_class(name) == canonical for name in names):
            ordered.append(canonical)
    for name in names:
        canonical = canonicalize_class(name)
        if canonical not in ordered:
            ordered.append(canonical)
    index = {name: i for i, name in enumerate(ordered)}
    id_map = {old: index[canonicalize_class(name)] for old, name in enumerate(names)}
    return ordered, id_map


def rewrite_label_line(line: str, id_map: dict[int, int]) -> str | None:
    stripped = line.strip()
    if not stripped:
        return None
    parts = stripped.split()
    old = int(float(parts[0]))
    if old not in id_map:
        raise KeyError(f"label class id {old} is outside names")
    parts[0] = str(id_map[old])
    return " ".join(parts)


def _split_dirs(root: Path) -> list[tuple[str, Path]]:
    found = []
    for name in ("train", "valid", "val", "test"):
        images = root / name / "images"
        labels = root / name / "labels"
        if images.is_dir() and labels.is_dir():
            found.append((name, root / name))
    return found


def prepare_dataset(src: Path, dst: Path) -> Path:
    """Build ``dst`` from ``src``. Returns the written data.yaml path."""
    src = src.resolve()
    dst = dst.resolve()
    data_file = src / "data.yaml"
    if not data_file.is_file():
        raise FileNotFoundError(
            f"No data.yaml at {data_file}. Download the Roboflow set first:\n"
            "  ROBOFLOW_API_KEY=... python ai/scripts/download_roboflow_dataset.py"
        )
    names = parse_names(data_file.read_text(encoding="utf-8"))
    new_names, id_map = remap_plan(names)
    splits = _split_dirs(src)
    if not splits:
        raise FileNotFoundError(f"No train/valid/test image folders under {src}")
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    label_count = 0
    for split_name, split_dir in splits:
        out_images = dst / split_name / "images"
        out_labels = dst / split_name / "labels"
        out_images.mkdir(parents=True)
        out_labels.mkdir(parents=True)
        for image in (split_dir / "images").iterdir():
            if image.name.startswith("."):
                continue
            target = out_images / image.name
            try:
                os.symlink(image.resolve(), target)
            except OSError:
                shutil.copy2(image, target)
        for label in (split_dir / "labels").glob("*.txt"):
            rewritten = []
            for line in label.read_text(encoding="utf-8").splitlines():
                updated = rewrite_label_line(line, id_map)
                if updated:
                    rewritten.append(updated)
                    label_count += 1
            (out_labels / label.name).write_text(
                ("\n".join(rewritten) + "\n") if rewritten else "",
                encoding="utf-8",
            )
    yaml_lines = [
        f"path: {dst.as_posix()}",
        "train: train/images",
    ]
    if (dst / "valid").is_dir():
        yaml_lines.append("val: valid/images")
    elif (dst / "val").is_dir():
        yaml_lines.append("val: val/images")
    if (dst / "test").is_dir():
        yaml_lines.append("test: test/images")
    yaml_lines.append(f"nc: {len(new_names)}")
    yaml_lines.append("names:")
    for name in new_names:
        yaml_lines.append(f"  - {name}")
    yaml_lines.append("")
    out_yaml = dst / "data.yaml"
    out_yaml.write_text("\n".join(yaml_lines), encoding="utf-8")
    summary = dst / "remap.txt"
    summary.write_text(
        "source names:\n"
        + "\n".join(f"  {i}: {name} -> {new_names[id_map[i]]} ({id_map[i]})" for i, name in enumerate(names))
        + f"\n\nlabel rows rewritten: {label_count}\n",
        encoding="utf-8",
    )
    return out_yaml


def main() -> int:
    ai_dir = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--src",
        type=Path,
        default=ai_dir / "datasets" / "roboflow-drowning",
    )
    parser.add_argument(
        "--dst",
        type=Path,
        default=ai_dir / "datasets" / "roboflow-drowning-4cls",
    )
    args = parser.parse_args()
    try:
        yaml_path = prepare_dataset(args.src, args.dst)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {yaml_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
