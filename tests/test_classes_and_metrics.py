"""Class mapping, box distance, and confusion-matrix checks. No model weights."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ai"))

from boxes import box_iou, iou_distance  # noqa: E402
from classes import (  # noqa: E402
    CANONICAL_CLASSES,
    apply_class_floor,
    canonicalize_class,
    class_risk_floor,
    is_target_class,
)
from metrics import confusion_matrix, micro_scores, per_class_scores  # noqa: E402


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Drowning", "drowning"),
        ("drowning", "drowning"),
        ("Swimming", "swimming"),
        ("swimming", "swimming"),
        ("Out of Water", "out_of_water"),
        ("out of water", "out_of_water"),
        ("out_of_water", "out_of_water"),
        ("person", "person"),
        ("Person", "person"),
        ("swimmer", "person"),
        ("", "person"),
        (None, "person"),
    ],
)
def test_duplicate_labels_collapse(raw, expected):
    assert canonicalize_class(raw) == expected
    assert canonicalize_class(canonicalize_class(raw)) == expected


def test_seven_roboflow_names_are_four_classes():
    published = [
        "Drowning",
        "Out of Water",
        "Swimming",
        "drowning",
        "out of water",
        "person",
        "swimming",
    ]
    collapsed = {canonicalize_class(name) for name in published}
    assert collapsed == set(CANONICAL_CLASSES)


def test_unknown_label_is_not_forced_to_person():
    assert canonicalize_class("boat") == "boat"
    assert is_target_class("boat") is False
    assert is_target_class("Drowning") is True


def test_drowning_floor_scales_with_confidence():
    low, factor = class_risk_floor("Drowning", 0.5)
    high, _factor = class_risk_floor("drowning", 0.9)
    assert factor == "detection_class_drowning"
    assert 50 <= low < 70
    assert high >= 70
    assert class_risk_floor("Swimming", 0.99) == (0.0, None)


def test_drowning_floor_raises_a_low_motion_score():
    score, factor, floor = apply_class_floor(10, "drowning", 0.8)
    assert factor == "detection_class_drowning"
    assert score == floor
    assert score > 10


def test_identical_boxes_are_zero_distance():
    box = (0, 0, 10, 10)
    assert box_iou(box, box) == pytest.approx(1.0)
    assert iou_distance(box, box) == pytest.approx(0.0)


def test_tracker_threshold_accepts_moderate_iou():
    # Equal boxes shifted by half a width have IoU 1/3 (distance 2/3).
    # That is inside the 0.70 threshold and outside the old 0.2 threshold.
    box_a = (0, 0, 10, 10)
    box_b = (5, 0, 15, 10)
    distance = iou_distance(box_a, box_b)
    assert box_iou(box_a, box_b) == pytest.approx(1 / 3)
    assert distance < 0.70
    assert distance > 0.2


def test_confusion_matrix_counts_misses_and_swaps():
    images = [
        {
            "gt": [
                {"cls": "drowning", "box": (0, 0, 10, 10)},
                {"cls": "swimming", "box": (50, 50, 80, 80)},
            ],
            "pred": [
                {"cls": "drowning", "box": (1, 1, 11, 11), "conf": 0.9},
                {"cls": "person", "box": (51, 51, 81, 81), "conf": 0.4},
            ],
        },
        {
            "gt": [{"cls": "out_of_water", "box": (0, 0, 8, 8)}],
            "pred": [],
        },
    ]
    labels = list(CANONICAL_CLASSES)
    matrix = confusion_matrix(images, labels, iou_threshold=0.5)
    scores = {row["class"]: row for row in per_class_scores(matrix, labels)}
    assert scores["drowning"]["tp"] == 1
    assert scores["swimming"]["fn"] == 1
    assert scores["person"]["fp"] == 1
    assert scores["out_of_water"]["fn"] == 1
    micro = micro_scores(list(scores.values()))
    assert micro["tp"] == 1
    assert micro["fp"] == 1
    assert micro["fn"] == 2
