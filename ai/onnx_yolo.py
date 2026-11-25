"""YOLOv8 inference with ONNX Runtime and NumPy.

No torch and no ultralytics. The exported graph does not include NMS, so
boxes are filtered and suppressed here. Class names go through the same
canonical map as the PyTorch detector.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path

import numpy as np

from classes import CANONICAL_ORDER, canonicalize_class

COCO_PERSON_INDEX = 0


def letterbox(image: np.ndarray, new_shape: int) -> tuple[np.ndarray, float, tuple[float, float]]:
    """Resize with unchanged aspect ratio and pad to a square. Returns image, ratio, (pad_w, pad_h)."""
    import cv2

    height, width = image.shape[:2]
    ratio = min(new_shape / height, new_shape / width)
    resized = (int(round(width * ratio)), int(round(height * ratio)))
    if resized != (width, height):
        image = cv2.resize(image, resized, interpolation=cv2.INTER_LINEAR)
    pad_w = (new_shape - resized[0]) / 2
    pad_h = (new_shape - resized[1]) / 2
    top, bottom = int(round(pad_h - 0.1)), int(round(pad_h + 0.1))
    left, right = int(round(pad_w - 0.1)), int(round(pad_w + 0.1))
    padded = cv2.copyMakeBorder(image, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))
    return padded, ratio, (float(left), float(top))


def nms_indices(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float) -> list[int]:
    """Greedy NMS. ``boxes`` are xyxy. Returns kept indexes, highest score first."""
    if len(boxes) == 0:
        return []
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]
    areas = np.maximum(0.0, x2 - x1) * np.maximum(0.0, y2 - y1)
    order = scores.argsort()[::-1]
    keep: list[int] = []
    while order.size > 0:
        current = int(order[0])
        keep.append(current)
        if order.size == 1:
            break
        rest = order[1:]
        xx1 = np.maximum(x1[current], x1[rest])
        yy1 = np.maximum(y1[current], y1[rest])
        xx2 = np.minimum(x2[current], x2[rest])
        yy2 = np.minimum(y2[current], y2[rest])
        inter = np.maximum(0.0, xx2 - xx1) * np.maximum(0.0, yy2 - yy1)
        union = areas[current] + areas[rest] - inter
        iou = np.divide(inter, union, out=np.zeros_like(inter), where=union > 0)
        order = rest[iou <= iou_threshold]
    return keep


def _parse_names(metadata: dict, class_count: int) -> dict[int, str]:
    raw = ""
    if metadata:
        raw = metadata.get("names") or metadata.get("classes") or ""
    if raw:
        try:
            parsed = ast.literal_eval(raw)
        except (SyntaxError, ValueError):
            parsed = None
        if isinstance(parsed, dict):
            return {int(key): str(value) for key, value in parsed.items()}
        if isinstance(parsed, (list, tuple)):
            return {index: str(name) for index, name in enumerate(parsed)}
    if class_count == len(CANONICAL_ORDER):
        return {index: name for index, name in enumerate(CANONICAL_ORDER)}
    if class_count == 80:
        return {COCO_PERSON_INDEX: "person"}
    return {index: f"class_{index}" for index in range(class_count)}


class OnnxYolo:
    """One ONNX Runtime session. Call ``detect`` with a BGR frame."""

    def __init__(self, model_path: str, imgsz: int | None = None):
        import onnxruntime as ort

        path = Path(model_path)
        if not path.is_file():
            raise FileNotFoundError(
                f"ONNX weights not found at {path}. "
                "The Render image ships ai/models/yolov8n.onnx. "
                "Set MODEL_URL to a .onnx file to override it."
            )
        threads = max(1, int(os.getenv("ORT_THREADS", "1")))
        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session = ort.InferenceSession(str(path), sess_options=options, providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        shape = self.session.get_inputs()[0].shape
        fixed = None
        if len(shape) == 4 and isinstance(shape[2], int) and isinstance(shape[3], int):
            fixed = int(shape[2])
        requested = int(imgsz if imgsz is not None else os.getenv("INFERENCE_IMGSZ", "640"))
        # The shipped yolov8n.onnx graph is fixed at 640. A smaller env value
        # cannot change that file; a dynamic export would honor the request.
        self.imgsz = fixed or requested
        if fixed and requested != fixed:
            print(f"ONNX input is fixed at {fixed}; ignoring INFERENCE_IMGSZ={requested}")
        self.path = str(path)
        # Names are filled on the first output, once the channel count is known.
        self.names: dict[int, str] = {}
        self._metadata = dict(self.session.get_modelmeta().custom_metadata_map or {})
        self.coco_person_only = False

    def detect(self, frame: np.ndarray, conf_thres: float, iou_thres: float) -> list[tuple]:
        import cv2

        original_height, original_width = frame.shape[:2]
        max_width = int(os.getenv("MAX_FRAME_WIDTH", "0") or "0")
        scale = 1.0
        if max_width > 0 and original_width > max_width:
            scale = max_width / original_width
            frame = cv2.resize(
                frame,
                (max_width, max(1, int(round(original_height * scale)))),
                interpolation=cv2.INTER_AREA,
            )
        padded, ratio, (pad_w, pad_h) = letterbox(frame, self.imgsz)
        blob = padded[:, :, ::-1].transpose(2, 0, 1)
        blob = np.ascontiguousarray(blob, dtype=np.float32) / 255.0
        outputs = self.session.run(None, {self.input_name: blob[None]})
        prediction = np.squeeze(outputs[0])
        if prediction.ndim != 2:
            return []
        if prediction.shape[0] < prediction.shape[1]:
            prediction = prediction.T
        class_count = prediction.shape[1] - 4
        if class_count < 1:
            return []
        if not self.names:
            self.names = _parse_names(self._metadata, class_count)
            self.coco_person_only = class_count == 80

        scores_all = prediction[:, 4:]
        class_ids = scores_all.argmax(axis=1)
        confidences = scores_all[np.arange(len(scores_all)), class_ids]
        mask = confidences >= conf_thres
        if self.coco_person_only:
            mask = mask & (class_ids == COCO_PERSON_INDEX)
        if not np.any(mask):
            return []

        boxes = prediction[mask, :4].astype(np.float32)
        confidences = confidences[mask]
        class_ids = class_ids[mask]
        xyxy = np.empty_like(boxes)
        xyxy[:, 0] = boxes[:, 0] - boxes[:, 2] / 2
        xyxy[:, 1] = boxes[:, 1] - boxes[:, 3] / 2
        xyxy[:, 2] = boxes[:, 0] + boxes[:, 2] / 2
        xyxy[:, 3] = boxes[:, 1] + boxes[:, 3] / 2
        xyxy[:, [0, 2]] -= pad_w
        xyxy[:, [1, 3]] -= pad_h
        xyxy /= ratio
        if scale != 1.0:
            xyxy /= scale
        xyxy[:, [0, 2]] = xyxy[:, [0, 2]].clip(0, original_width - 1)
        xyxy[:, [1, 3]] = xyxy[:, [1, 3]].clip(0, original_height - 1)

        kept: list[int] = []
        for class_id in np.unique(class_ids):
            indexes = np.where(class_ids == class_id)[0]
            local = nms_indices(xyxy[indexes], confidences[indexes], iou_thres)
            kept.extend(int(indexes[item]) for item in local)

        detections = []
        for index in kept:
            name = canonicalize_class(self.names.get(int(class_ids[index]), "person"))
            x1, y1, x2, y2 = (int(round(value)) for value in xyxy[index])
            if x2 <= x1 or y2 <= y1:
                continue
            detections.append((x1, y1, x2, y2, float(confidences[index]), name))
        return detections
