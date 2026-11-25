"""Bounding-box geometry shared by the tracker and evaluation."""

from __future__ import annotations


def box_iou(box_a, box_b) -> float:
    """Intersection over union for boxes ``(x1, y1, x2, y2)``."""
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    if union <= 0:
        return 0.0
    return float(inter / union)


def iou_distance(box_a, box_b) -> float:
    """Norfair distance: ``1 - IoU``. Lower means a better match.

    A distance threshold of 0.70 accepts pairs with IoU >= 0.30.
    The previous default threshold of 0.2 required IoU >= 0.8, which
    drops tracks whenever ``FRAME_SKIP`` lets a swimmer move between
    processed frames.
    """
    return 1.0 - box_iou(box_a, box_b)
