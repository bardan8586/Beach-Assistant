"""Detection metrics that do not require Ultralytics.

Used by ``scripts/evaluate.py`` and by unit tests so per-class precision,
recall and a confusion matrix stay reproducible even when the dataset or
weights are absent.
"""

from __future__ import annotations

from typing import Iterable, Sequence

from boxes import box_iou


def greedy_match(
    ground_truth: Sequence[dict],
    predictions: Sequence[dict],
    iou_threshold: float = 0.5,
) -> tuple[list[tuple[int, int, float]], list[int], list[int]]:
    """Match predictions to ground truth by descending IoU.

    Each item needs ``cls`` and ``box`` (x1, y1, x2, y2). Predictions may
    also carry ``conf``; higher confidence is preferred when IoU ties.
    """
    pairs: list[tuple[float, float, int, int]] = []
    for gi, gt in enumerate(ground_truth):
        for pi, pred in enumerate(predictions):
            iou = box_iou(gt["box"], pred["box"])
            if iou >= iou_threshold:
                conf = float(pred.get("conf", 1.0))
                pairs.append((iou, conf, gi, pi))
    pairs.sort(key=lambda row: (row[0], row[1]), reverse=True)
    used_gt: set[int] = set()
    used_pred: set[int] = set()
    matched: list[tuple[int, int, float]] = []
    for iou, _conf, gi, pi in pairs:
        if gi in used_gt or pi in used_pred:
            continue
        used_gt.add(gi)
        used_pred.add(pi)
        matched.append((gi, pi, iou))
    unmatched_gt = [i for i in range(len(ground_truth)) if i not in used_gt]
    unmatched_pred = [i for i in range(len(predictions)) if i not in used_pred]
    return matched, unmatched_gt, unmatched_pred


def confusion_matrix(
    images: Iterable[dict],
    labels: Sequence[str],
    iou_threshold: float = 0.5,
) -> list[list[int]]:
    """Rows are ground truth, columns are predictions, plus a background bin.

    The last index is background: false negatives land in
    ``matrix[class][background]``, false positives in ``matrix[background][class]``.
    """
    names = list(labels)
    index = {name: i for i, name in enumerate(names)}
    bg = len(names)
    size = bg + 1
    matrix = [[0 for _ in range(size)] for _ in range(size)]
    for image in images:
        gt = list(image.get("gt") or [])
        pred = list(image.get("pred") or [])
        matched, unmatched_gt, unmatched_pred = greedy_match(gt, pred, iou_threshold)
        for gi, pi, _iou in matched:
            gt_name = gt[gi]["cls"]
            pred_name = pred[pi]["cls"]
            matrix[index.get(gt_name, bg)][index.get(pred_name, bg)] += 1
        for gi in unmatched_gt:
            matrix[index.get(gt[gi]["cls"], bg)][bg] += 1
        for pi in unmatched_pred:
            matrix[bg][index.get(pred[pi]["cls"], bg)] += 1
    return matrix


def per_class_scores(matrix: Sequence[Sequence[int]], labels: Sequence[str]) -> list[dict]:
    """Precision, recall and F1 per class. Background is excluded from the rows reported."""
    bg = len(labels)
    scores = []
    for i, name in enumerate(labels):
        tp = matrix[i][i]
        fn = matrix[i][bg] + sum(matrix[i][j] for j in range(bg) if j != i)
        fp = matrix[bg][i] + sum(matrix[j][i] for j in range(bg) if j != i)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        support = sum(matrix[i][:bg]) + matrix[i][bg]
        scores.append(
            {
                "class": name,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "support": support,
                "tp": tp,
                "fp": fp,
                "fn": fn,
            }
        )
    return scores


def micro_scores(per_class: Sequence[dict]) -> dict:
    tp = sum(row["tp"] for row in per_class)
    fp = sum(row["fp"] for row in per_class)
    fn = sum(row["fn"] for row in per_class)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn}
