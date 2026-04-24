#!/usr/bin/env python3
"""
Step 2: Download Drowning Detection dataset from Roboflow Universe.
Uses ROBOFLOW_API_KEY from environment.

Usage:
  ROBOFLOW_API_KEY=your_key ./venv/bin/python scripts/download_roboflow_dataset.py
  # or, from ai/ with .env loaded:
  python scripts/download_roboflow_dataset.py
"""

import os
import sys
from pathlib import Path

# Add ai/ to path
ai_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ai_dir))

def _load_env():
    """
    Load ROBOFLOW_API_KEY from ai/.env (or ai/.ENV) if present.
    We intentionally do not read backend/.env here.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    env_path_lower = ai_dir / ".env"
    env_path_upper = ai_dir / ".ENV"
    if env_path_lower.exists():
        load_dotenv(dotenv_path=env_path_lower)
    elif env_path_upper.exists():
        load_dotenv(dotenv_path=env_path_upper)


def main():
    _load_env()

    api_key = os.environ.get("ROBOFLOW_API_KEY")
    if not api_key:
        print("Error: ROBOFLOW_API_KEY not set.")
        print("  Run: ROBOFLOW_API_KEY=your_key python scripts/download_roboflow_dataset.py")
        sys.exit(1)

    try:
        from roboflow import Roboflow
    except ImportError:
        print("Error: roboflow not installed. Run: pip install roboflow")
        sys.exit(1)

    # Output location: ai/datasets/roboflow-drowning/
    output_dir = ai_dir / "datasets" / "roboflow-drowning"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Connecting to Roboflow...")
    rf = Roboflow(api_key=api_key)
    project = rf.workspace("machine-learning-computer-vision").project(
        "drowning-detection-and-prevention-in-swimming-pools-ooq1f"
    )
    version = project.version(2)  # Version 1 not available; v2 has train/valid/test
    print("Downloading dataset (YOLOv8 format)...")
    dataset = version.download("yolov8", location=str(output_dir), overwrite=True)

    print(f"\nDataset saved to: {output_dir.absolute()}")
    print("Next step: run training with this data.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
