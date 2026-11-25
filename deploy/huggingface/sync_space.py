#!/usr/bin/env python3
"""Create or update a Hugging Face Docker Space from this repo.

The Space repository is not this GitHub repo. This script copies the API,
the AI worker, the root Dockerfile, and deploy/huggingface/README.md (the
file with sdk: docker) into a temporary tree and uploads that tree.

Usage, from the repo root:

    export HF_TOKEN=hf_your_write_token
    python deploy/huggingface/sync_space.py your-user/beach-assistant

Requires huggingface_hub. The GitHub Action installs it. Locally:

    pip install huggingface_hub
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPACE_README = Path(__file__).resolve().parent / "README.md"

SKIP_DIR_NAMES = {
    "__pycache__",
    ".venv",
    "venv",
    "datasets",
    "runs",
    "uploads",
    ".git",
    "node_modules",
}
SKIP_SUFFIXES = {".pyc", ".pt", ".onnx", ".mp4", ".mov"}


def _ignore(_directory: str, names: list[str]) -> set[str]:
    skipped = set()
    for name in names:
        if name in SKIP_DIR_NAMES or name.startswith("."):
            skipped.add(name)
            continue
        if Path(name).suffix.lower() in SKIP_SUFFIXES:
            skipped.add(name)
    return skipped


def stage_space(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SPACE_README, destination / "README.md")
    shutil.copy2(ROOT / "Dockerfile", destination / "Dockerfile")
    shutil.copy2(ROOT / ".dockerignore", destination / ".dockerignore")
    for folder in ("backend", "ai"):
        shutil.copytree(
            ROOT / folder,
            destination / folder,
            ignore=_ignore,
            dirs_exist_ok=True,
        )


def main() -> int:
    if len(sys.argv) != 2 or "/" not in sys.argv[1]:
        print("Usage: python deploy/huggingface/sync_space.py USER/beach-assistant", file=sys.stderr)
        return 1
    space_id = sys.argv[1].strip()
    token = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
    if not token:
        print("Set HF_TOKEN to a Hugging Face token that can write this Space.", file=sys.stderr)
        return 1
    try:
        from huggingface_hub import HfApi
    except ImportError:
        print("pip install huggingface_hub", file=sys.stderr)
        return 1

    api = HfApi(token=token)
    api.create_repo(
        repo_id=space_id,
        repo_type="space",
        space_sdk="docker",
        exist_ok=True,
        private=False,
    )
    with tempfile.TemporaryDirectory(prefix="beach-space-") as temporary:
        stage = Path(temporary) / "space"
        stage_space(stage)
        print(f"Uploading {stage} to https://huggingface.co/spaces/{space_id}")
        api.upload_folder(
            repo_id=space_id,
            repo_type="space",
            folder_path=str(stage),
            commit_message="Sync Beach Assistant API",
        )
    print(f"Space: https://huggingface.co/spaces/{space_id}")
    print("Runtime URL: https://" + space_id.replace("/", "-") + ".hf.space")
    print("Confirm Settings → Hardware is CPU basic. Leave PORT unset.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
