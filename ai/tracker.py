"""
Multi-object person tracking using ByteTrack for real-time streaming.

Design Notes:
- ByteTrack chosen for speed, simplicity, and free license (no deep feature extraction required).
- No facial or biometric features are used—tracking is purely box-based on motion/overlap.
- Each person is assigned a stable integer ID during their presence in the scene.
- Timestamps are maintained for each tracker (first seen, last seen).
- Occlusion robustness: tracks are kept 'alive' for a few frames even if detections disappear.
- Ready for integration downstream (behavior analysis, alerting, etc).

Dependencies (install via pip if missing): 
  pip install norfair

  (We adopt 'norfair' for a pure-Python ByteTrack implementation for easy distribution.)

API:
- PersonTracker.update(detections, timestamp) --> returns list of TrackedPerson

"""

from typing import List, Tuple, Dict, Optional, Any
import numpy as np
import time

# Use Norfair's ByteTrack implementation for ease of deployment
try:
    from norfair import Detection, Tracker, Video, draw_tracked_objects
    from norfair.tracker import TrackedObject
except ImportError:
    # If norfair is not installed, raise a meaningful error
    raise ImportError("Please install norfair: pip install norfair")

class TrackedPerson:
    """
    Data structure for one tracked person.
    """
    def __init__(self,
                 track_id: int,
                 bbox: Tuple[int, int, int, int],
                 confidence: float,
                 first_seen: float,
                 last_seen: float,
                 class_name: str = "person"):
        self.track_id = track_id
        self.bbox = bbox  # (x1, y1, x2, y2)
        self.confidence = confidence
        self.first_seen = first_seen  # unix timestamp
        self.last_seen = last_seen    # unix timestamp
        self.class_name = class_name  # e.g. Drowning, Swimming, person (from fine-tuned model)

    def to_dict(self):
        return {
            "track_id": self.track_id,
            "bbox": self.bbox,
            "confidence": self.confidence,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "class_name": self.class_name,
        }

class PersonTracker:
    """
    Multi-person tracker using ByteTrack (via norfair) for robust ID assignment in video streams.
    
    Usage:
        tracker = PersonTracker()
        tracked = tracker.update(detections, timestamp)

    detections: list of (x1, y1, x2, y2, conf) for each person in frame
    timestamp: float (seconds, e.g. from time.time())
    """
    def __init__(
        self,
        max_staleness: float = 1.0,        # seconds without detection before removing track
        min_detection_conf: float = 0.2,   # ignores extremely weak boxes (should match detector)
        iou_threshold: float = 0.2,        # box association IOU
    ):
        """
        max_staleness: after how many seconds with no detection do we delete a track?
        iou_threshold: ByteTrack track-to-box association; lower=harder to match
        """
        self.min_detection_conf = min_detection_conf
        self.iou_threshold = iou_threshold
        self.max_staleness = max_staleness
        
        # Norfair/ByteTrack config: only 2D boxes (no appearance/descriptors)
        self.tracker = Tracker(
            distance_function=self._iou_distance,
            distance_threshold=self.iou_threshold,
            initialization_delay=0,  # start tracks immediately
            hit_counter_max=10,      # how many missed frames before removing a track
            past_detections_length=2
        )
        # For timestamps
        self.first_seen: Dict[int, float] = {}  # track_id -> first time seen
        self.last_seen: Dict[int, float] = {}   # track_id -> last time this id matched a box

    @staticmethod
    def _bbox_to_points(bbox: Tuple[int, int, int, int]) -> np.ndarray:
        """
        Norfair expects detections as array-of-points, for boxes we use (center_x, center_y)
        """
        x1, y1, x2, y2 = bbox
        center = np.array([[ (x1 + x2) / 2, (y1 + y2) / 2 ]])
        return center

    @staticmethod
    def _iou_distance(detection: Detection, tracked_object: TrackedObject) -> float:
        """
        Computes 1-IOU (for minimization) between detection and tracker.
        Norfair expects distance_function to return low values for *closer* objects.
        """
        # Each norfair Detection/tracker stores (x1, y1, x2, y2) in .data["bbox"]
        box_a = detection.data["bbox"]
        box_b = tracked_object.last_detection.data["bbox"]
        # Calculate intersection-over-union
        xA = max(box_a[0], box_b[0])
        yA = max(box_a[1], box_b[1])
        xB = min(box_a[2], box_b[2])
        yB = min(box_a[3], box_b[3])
        interW = max(0, xB - xA)
        interH = max(0, yB - yA)
        interArea = interW * interH
        areaA = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
        areaB = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
        unionArea = areaA + areaB - interArea
        if unionArea == 0:
            return 1.0  # far
        iou = interArea / unionArea
        return 1 - iou  # want small distances to mean better match

    def update(
        self,
        detections: List[Tuple[int, int, int, int, float]],
        timestamp: Optional[float] = None
    ) -> List[TrackedPerson]:
        """
        Run tracking step for the current frame.
        detections: list of (x1, y1, x2, y2, conf) or (x1, y1, x2, y2, conf, class_name)
        timestamp: current frame time (seconds). If None, uses time.time().
        Returns list of TrackedPerson visible in this frame.
        """
        if timestamp is None:
            timestamp = time.time()
        norfair_detections = []
        for det in detections:
            x1, y1, x2, y2, conf = det[0], det[1], det[2], det[3], det[4]
            class_name = det[5] if len(det) > 5 else "person"
            if conf < self.min_detection_conf:
                continue
            points = self._bbox_to_points((x1, y1, x2, y2))
            norfair_det = Detection(
                points=points,
                scores=np.array([conf]),
                data={"bbox": np.array([x1, y1, x2, y2]),
                      "confidence": conf,
                      "class_name": class_name}
            )
            norfair_detections.append(norfair_det)

        tracked_objects = self.tracker.update(norfair_detections)
        results = []
        for obj in tracked_objects:
            tid = obj.id
            detection = obj.last_detection
            bbox = tuple(int(v) for v in detection.data["bbox"])
            conf = float(detection.data["confidence"])
            class_name = detection.data.get("class_name", "person")
            if tid not in self.first_seen:
                self.first_seen[tid] = timestamp
            self.last_seen[tid] = timestamp
            person = TrackedPerson(
                track_id=tid,
                bbox=bbox,
                confidence=conf,
                first_seen=self.first_seen[tid],
                last_seen=self.last_seen[tid],
                class_name=class_name,
            )
            results.append(person)

        # Clean up old track timestamps (not strictly needed per-frame, but helps)
        stale_ids = [
            tid for tid, last in self.last_seen.items()
            if (timestamp - last) > self.max_staleness
        ]
        for tid in stale_ids:
            self.first_seen.pop(tid, None)
            self.last_seen.pop(tid, None)

        return results

# Example Usage:
# ------------------
# from ai.tracker import PersonTracker
# tracker = PersonTracker()
# while True:
#     detections = person_detector(frame)  # list of (x1,y1,x2,y2,conf)
#     tracked_people = tracker.update(detections, timestamp=now)
#     for track in tracked_people:
#         print(track.to_dict())
#
# This will assign persistent track IDs, smooth out detection dropout, and enable downstream logic.
