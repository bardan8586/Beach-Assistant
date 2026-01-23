from typing import List, Tuple, Any, Optional
import os
import cv2
import base64
import requests
import json

class Detector:
    """
    Unified detector supporting both local YOLOv8 models and Roboflow Inference API.
    """
    def __init__(self, 
                 model_type: str = "yolo",  # "yolo" or "roboflow"
                 model_name: str = "yolov8s.pt",  # Better default: small instead of nano
                 roboflow_api_key: Optional[str] = None,
                 roboflow_model_id: Optional[str] = None,
                 roboflow_version: Optional[int] = None,
                 device: Optional[str] = None,
                 enable_pose: bool = False):  # NEW: Enable pose estimation
        """
        Initialize detector with either YOLOv8 or Roboflow.
        
        Args:
            model_type: "yolo" for local YOLOv8, "roboflow" for Roboflow Inference API
            model_name: YOLOv8 model name (yolov8n.pt, yolov8s.pt, yolov8m.pt, etc.)
            roboflow_api_key: Roboflow API key (from environment or parameter)
            roboflow_model_id: Roboflow model ID (e.g., "swimmer-detection/1")
            roboflow_version: Roboflow model version number
            device: 'cuda', 'cpu', or None (auto-detect)
            enable_pose: Whether to enable pose estimation (YOLOv8-Pose)
        """
        self.model_type = model_type.lower()
        self.model = None
        self.pose_model = None  # NEW: Separate model for pose estimation
        self.enable_pose = enable_pose
        self.roboflow_config = {}
        
        if self.model_type == "roboflow":
            self._init_roboflow(roboflow_api_key, roboflow_model_id, roboflow_version)
        else:
            self._init_yolo(model_name, device)
            
            # Initialize pose model if enabled
            if self.enable_pose:
                self._init_pose_model(device)
    
    def _init_yolo(self, model_name: str, device: Optional[str]):
        """Initialize YOLOv8 model."""
        from ultralytics import YOLO
        import torch
        
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        
        self.device = device
        print(f"Loading YOLOv8 model: {model_name} on {device}")
        self.model = YOLO(model_name)
        self.model.to(device)
        print(f"✅ YOLOv8 model loaded successfully")
    
    def _init_pose_model(self, device: Optional[str]):
        """Initialize YOLOv8-Pose model for body keypoint detection."""
        from ultralytics import YOLO
        
        print(f"Loading YOLOv8-Pose model for drowning detection...")
        # Use YOLOv8n-pose for real-time performance
        self.pose_model = YOLO("yolov8n-pose.pt")
        self.pose_model.to(device or self.device)
        print(f"✅ YOLOv8-Pose model loaded successfully")
    
    def _init_roboflow(self, api_key: Optional[str], model_id: Optional[str], version: Optional[int]):
        """Initialize Roboflow Inference API connection."""
        # Get from environment if not provided
        api_key = api_key or os.getenv("ROBOFLOW_API_KEY")
        model_id = model_id or os.getenv("ROBOFLOW_MODEL_ID")
        version = version or int(os.getenv("ROBOFLOW_VERSION", "1"))
        
        if not api_key or not model_id:
            raise ValueError(
                "Roboflow requires ROBOFLOW_API_KEY and ROBOFLOW_MODEL_ID. "
                "Set them as environment variables or pass as parameters."
            )
        
        self.roboflow_config = {
            "api_key": api_key,
            "model_id": model_id,
            "version": version,
            "base_url": f"https://detect.roboflow.com/{model_id}/{version}"
        }
        print(f"✅ Roboflow Inference API configured: {model_id} v{version}")
    
    def detect_people(self, 
                      frame, 
                      conf_thres: float = 0.5,
                      iou_thres: float = 0.5,
                      min_size: Optional[int] = None) -> List[Tuple[int, int, int, int, float]]:
        """
        Detect people in a frame.
        
        Args:
            frame: Input image (numpy array, BGR as from OpenCV)
            conf_thres: Minimum confidence threshold
            iou_thres: Non-maximum suppression threshold
            min_size: Minimum bounding box size (optional, for filtering small detections)
        
        Returns:
            List of (x1, y1, x2, y2, conf) tuples for each detected person
        """
        if self.model_type == "roboflow":
            detections = self._detect_roboflow(frame, conf_thres)
        else:
            detections = self._detect_yolo(frame, conf_thres, iou_thres, imgsz=None)
        
        # Filter by minimum size if specified (for far objects, use lower threshold)
        if min_size is not None:
            detections = [(x1, y1, x2, y2, conf) for x1, y1, x2, y2, conf in detections
                         if (x2 - x1) >= min_size and (y2 - y1) >= min_size]
        
        return detections
    
    def detect_poses(self, frame, conf_thres: float = 0.5) -> dict:
        """
        Detect body keypoints for all people in frame using YOLOv8-Pose.
        
        Args:
            frame: Input image (numpy array, BGR)
            conf_thres: Minimum confidence threshold
            
        Returns:
            Dictionary mapping detection index to keypoints array (17, 3) [x, y, conf]
            Format: {0: keypoints_array, 1: keypoints_array, ...}
        """
        if not self.enable_pose or self.pose_model is None:
            return {}
        
        try:
            results = self.pose_model(
                frame,
                conf=conf_thres,
                verbose=False,
                device=self.device
            )
            
            result = results[0]
            poses = {}
            
            # Extract keypoints for each detection
            if hasattr(result, 'keypoints') and result.keypoints is not None:
                keypoints_data = result.keypoints.data.cpu().numpy()  # Shape: (num_people, 17, 3)
                
                for i, kp in enumerate(keypoints_data):
                    poses[i] = kp  # (17, 3) array of [x, y, confidence]
            
            return poses
        
        except Exception as e:
            print(f"⚠️  Pose detection error: {e}")
            return {}
    
    def _detect_yolo(self, frame, conf_thres: float, iou_thres: float, 
                    imgsz: Optional[int] = None) -> List[Tuple[int, int, int, int, float]]:
        """Run YOLOv8 detection."""
        try:
            # Use default image size (faster) - YOLOv8 handles scaling internally
            # Only use larger size if explicitly requested
            if imgsz is None:
                imgsz = 640  # Default YOLOv8 size for speed
            
            results = self.model(
                frame,
                conf=conf_thres,
                iou=iou_thres,
                classes=[0],  # COCO class index for 'person'
                verbose=False,
                device=self.model.device,
                imgsz=imgsz
            )
            
            result = results[0]
            detections = []
            
            for box, conf, cls in zip(result.boxes.xyxy.cpu().numpy(),
                                      result.boxes.conf.cpu().numpy(),
                                      result.boxes.cls.cpu().numpy()):
                if int(cls) != 0:
                    continue
                x1, y1, x2, y2 = map(int, box)
                detections.append((x1, y1, x2, y2, float(conf)))
            
            return detections
        except Exception as e:
            print(f"⚠️  Detection error: {e}")
            return []  # Return empty list on error instead of crashing
    
    def _detect_roboflow(self, frame, conf_thres: float) -> List[Tuple[int, int, int, int, float]]:
        """Run Roboflow Inference API detection."""
        # Encode frame as base64
        _, buffer = cv2.imencode('.jpg', frame)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        # Prepare request
        url = f"{self.roboflow_config['base_url']}?api_key={self.roboflow_config['api_key']}"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        try:
            response = requests.post(
                url,
                data=img_base64,
                headers=headers,
                timeout=5.0
            )
            response.raise_for_status()
            
            result = response.json()
            detections = []
            
            # Parse Roboflow response
            # Roboflow returns: {"predictions": [{"x": center_x, "y": center_y, "width": w, "height": h, "confidence": conf, "class": class_name}, ...]}
            for pred in result.get("predictions", []):
                # Filter for person/swimmer class
                class_name = pred.get("class", "").lower()
                if "person" in class_name or "swimmer" in class_name or "people" in class_name:
                    conf = float(pred.get("confidence", 0))
                    if conf < conf_thres:
                        continue
                    
                    # Convert center+size to x1,y1,x2,y2
                    center_x = float(pred["x"])
                    center_y = float(pred["y"])
                    width = float(pred["width"])
                    height = float(pred["height"])
                    
                    x1 = int(center_x - width / 2)
                    y1 = int(center_y - height / 2)
                    x2 = int(center_x + width / 2)
                    y2 = int(center_y + height / 2)
                    
                    detections.append((x1, y1, x2, y2, conf))
            
            return detections
        
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Roboflow API error: {e}")
            return []
        except Exception as e:
            print(f"⚠️  Error parsing Roboflow response: {e}")
            return []


# Legacy functions for backward compatibility
def load_yolov8_model(model_name: str = "yolov8s.pt", device: str = None):
    """
    Legacy function: Loads a YOLOv8 model (now defaults to 'small' for better accuracy).
    
    For new code, use Detector class instead.
    """
    detector = Detector(model_type="yolo", model_name=model_name, device=device)
    return detector.model


def detect_people(model: Any, 
                  frame, 
                  conf_thres: float = 0.5,
                  iou_thres: float = 0.5) -> List[Tuple[int, int, int, int, float]]:
    """
    Legacy function: Runs person detection on a frame.
    
    For new code, use Detector class instead.
    """
    # If model is a Detector instance, use it directly
    if isinstance(model, Detector):
        return model.detect_people(frame, conf_thres, iou_thres)
    
    # Otherwise, assume it's a YOLOv8 model (legacy behavior)
    results = model(
        frame,
        conf=conf_thres,
        iou=iou_thres,
        classes=[0],
        verbose=False,
        device=model.device
    )
    
    result = results[0]
    out = []
    for box, conf, cls in zip(result.boxes.xyxy.cpu().numpy(),
                              result.boxes.conf.cpu().numpy(),
                              result.boxes.cls.cpu().numpy()):
        if int(cls) != 0:
            continue
        x1, y1, x2, y2 = map(int, box)
        out.append((x1, y1, x2, y2, float(conf)))
    return out
