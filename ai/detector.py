from typing import List, Tuple, Any

def load_yolov8_model(model_name: str = "yolov8n.pt", device: str = None):
    """
    Loads a YOLOv8 model with GPU support if available.

    :param model_name: Name or path of the model weights.
    :param device: 'cuda', 'cpu', or None (auto). If None, tries CUDA first.
    :return: YOLOv8 model object.
    """
    # Lazy import to minimize startup time in pipelines
    from ultralytics import YOLO
    import torch

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    # The YOLO object will use the specified device
    model = YOLO(model_name)
    model.to(device)
    return model

def detect_people(
    model: Any, 
    frame, 
    conf_thres: float = 0.3, 
    iou_thres: float = 0.5
) -> List[Tuple[int, int, int, int, float]]:
    """
    Runs person detection on a frame using the provided YOLOv8 model.

    :param model: Loaded YOLOv8 model.
    :param frame: Input image (numpy array, BGR as from OpenCV).
    :param conf_thres: Minimum confidence for detection.
    :param iou_thres: Non-maximum suppression threshold.
    :return: List of (x1, y1, x2, y2, conf) tuples for each detected person.
    """
    # Use the model's __call__ for maximum throughput (no image display etc)
    results = model(
        frame,
        conf=conf_thres,
        iou=iou_thres,
        classes=[0],   # COCO class index for 'person'
        verbose=False,
        device=model.device
    )

    # Batch dimension is supported, but we expect a single frame
    result = results[0]
    out = []
    # Performance: results are on GPU, but boxes.xyxy is automatically moved to CPU
    for box, conf, cls in zip(result.boxes.xyxy.cpu().numpy(),
                              result.boxes.conf.cpu().numpy(),
                              result.boxes.cls.cpu().numpy()):
        # Only class==0 (person) should be returned, but sanity check:
        if int(cls) != 0:
            continue
        x1, y1, x2, y2 = map(int, box)
        out.append((x1, y1, x2, y2, float(conf)))
    return out

# Performance Notes:
# - Model and device selection happens once at init.
# - GPU inference if available; minibatch possible but kept to single-frame per call for streaming.
# - Avoids extra conversion/copying; expects OpenCV BGR numpy arrays throughout.
# - Results filtering and NMS is handled by Ultralytics inference call, classes=[0] avoids post-filter step.
# - For maximum throughput, instantiate and reuse the model across frames.

# Example usage in a video pipeline:
# 
# model = load_yolov8_model()
# while True:
#     frame = ...  # BGR image from stream
#     boxes = detect_people(model, frame)
#     for (x1, y1, x2, y2, conf) in boxes:
#         # Do something (draw, crop, alert)
#         pass

