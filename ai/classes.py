"""Canonical label space for the Roboflow drowning dataset.

The published set has 7 class names that are casing/spacing duplicates of
about 4 real classes:

    Drowning, drowning
    Swimming, swimming
    Out of Water, out of water
    person

Training on the duplicates splits supervision across identical concepts.
Inference maps every alias onto one canonical name before tracking and risk.
"""

from __future__ import annotations

CANONICAL_CLASSES = ("drowning", "out_of_water", "swimming", "person")

# Stable training order. Do not reorder: label indices in a remapped dataset
# follow this tuple, then any unknown names in first-seen order.
CANONICAL_ORDER = CANONICAL_CLASSES


def _normalize(name: str) -> str:
    text = str(name).strip().lower().replace("_", " ").replace("-", " ")
    return " ".join(text.split())


def canonicalize_class(name: str | None) -> str:
    """Map a raw detector or dataset label onto a stable class name.

    Unknown labels are returned in snake_case so they are not silently
    merged into ``person``. Empty input becomes ``person`` because the
    COCO fallback detector only emits people.
    """
    if name is None:
        return "person"
    key = _normalize(name)
    if not key:
        return "person"
    if "drown" in key:
        return "drowning"
    if "out" in key and "water" in key:
        return "out_of_water"
    if key in {"land", "on land", "beach", "shore"}:
        return "out_of_water"
    # Exact person words before the "swim" substring, so "swimmer" is not "swimming".
    if key in {"person", "people", "human", "swimmer", "swimmers", "pedestrian"}:
        return "person"
    if "swim" in key:
        return "swimming"
    if "person" in key or "people" in key:
        return "person"
    return key.replace(" ", "_")


def is_target_class(name: str | None) -> bool:
    """True when a detection belongs to the beach label set."""
    return canonicalize_class(name) in CANONICAL_CLASSES


def class_risk_floor(class_name: str | None, confidence: float = 1.0) -> tuple[float, str | None]:
    """Confidence-scaled risk floor from the detector label alone.

    A drowning label is evidence even when motion and pose have not caught
    up yet. Swimming and out-of-water labels add nothing. An unspecified
    person adds a small amount so an unknown activity is not treated as
    confirmed safe water behaviour.

    Returns ``(floor_0_to_100, factor_name)``. ``factor_name`` is None when
    the label should not change the score.
    """
    if class_name is None or not str(class_name).strip():
        return 0.0, None
    canonical = canonicalize_class(class_name)
    conf = max(0.0, min(1.0, float(confidence)))
    if canonical == "drowning":
        # 0.50 -> 62.5 (medium), 0.70 -> 77.5 (high), 1.00 -> 100
        return min(100.0, 25.0 + 75.0 * conf), "detection_class_drowning"
    if canonical == "person":
        return min(15.0, 15.0 * conf), "detection_class_person"
    return 0.0, None


def apply_class_floor(score: float, class_name: str | None, confidence: float = 1.0) -> tuple[float, str | None, float]:
    """Combine a base risk score with the class floor.

    Drowning replaces the score when the floor is higher (the label is a
    direct distress signal). Other contributions are added, then capped.
    """
    floor, factor = class_risk_floor(class_name, confidence)
    if not factor or floor <= 0:
        return min(100.0, max(0.0, score)), None, 0.0
    if factor == "detection_class_drowning":
        combined = max(score, floor)
    else:
        combined = score + floor
    return min(100.0, max(0.0, combined)), factor, floor
