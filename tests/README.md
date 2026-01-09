# Tests Directory

This directory contains test scripts and test data for the Beach Safety AI system.

## Structure

```
tests/
├── scripts/          # Test scripts
│   ├── test_detection.py    # Full detection pipeline test
│   └── quick_test.py        # Quick system validation
├── data/             # Test video files
│   └── beach_test.mp4
└── models/           # AI model files (for reference)
    └── yolov8n.pt
```

## Running Tests

From project root:

```bash
# Quick validation test
python tests/scripts/quick_test.py

# Full detection test with video
python tests/scripts/test_detection.py --source tests/data/beach_test.mp4
```

## Note

Models will auto-download if not found. The detector looks for models in the current working directory.
