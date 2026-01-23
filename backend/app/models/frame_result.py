"""
FrameResult - Unified Schema for AI → Backend → Frontend

This is the SINGLE SOURCE OF TRUTH for all frame processing data.
Every WebSocket message and stored result must match this schema.

Why this exists:
- Frontend needs video dimensions to correctly scale bounding boxes
- Frontend needs timestamps to sync with video playback
- Frontend needs consistent data structure for rendering
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class BoundingBox(BaseModel):
    """Bounding box in absolute video pixel coordinates (x, y, w, h)"""
    x: int = Field(..., description="Left edge X coordinate (pixels)")
    y: int = Field(..., description="Top edge Y coordinate (pixels)")
    w: int = Field(..., description="Width (pixels)")
    h: int = Field(..., description="Height (pixels)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "x": 100,
                "y": 200,
                "w": 80,
                "h": 150
            }
        }


class SwimmerData(BaseModel):
    """Data for a single tracked swimmer"""
    track_id: int = Field(..., description="Unique tracking ID")
    bbox: BoundingBox = Field(..., description="Bounding box in video coordinates")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence (0-1)")
    risk_score: int = Field(..., ge=0, le=100, description="Risk score (0-100)")
    risk_level: str = Field(..., description="Risk level: LOW, MEDIUM, HIGH, CRITICAL")
    behavior: str = Field(..., description="Behavior pattern: NORMAL, STATIONARY, ERRATIC, RAPID")
    zone: str = Field(..., description="Water zone: SAFE, CAUTION, DANGER")
    time_in_water: float = Field(default=0.0, description="Time in water (seconds)")
    distance_from_shore: Optional[float] = Field(None, description="Estimated distance from shore (meters)")
    
    # Motion metrics
    velocity: float = Field(default=0.0, description="Current velocity (pixels/second)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "track_id": 42,
                "bbox": {"x": 100, "y": 200, "w": 80, "h": 150},
                "confidence": 0.85,
                "risk_score": 45,
                "risk_level": "MEDIUM",
                "behavior": "NORMAL",
                "zone": "CAUTION",
                "time_in_water": 120.5,
                "distance_from_shore": 25.3,
                "velocity": 12.5
            }
        }


class SceneData(BaseModel):
    """Scene analysis data (shore, horizon, water conditions)"""
    shore_line_y: Optional[int] = Field(None, description="Shore line Y coordinate (pixels)")
    horizon_y: Optional[int] = Field(None, description="Horizon Y coordinate (pixels)")
    water_percentage: float = Field(default=0.0, ge=0.0, le=100.0, description="Percentage of frame that is water")
    visibility: float = Field(default=0.0, ge=0.0, le=1.0, description="Water visibility score (0-1)")
    wave_activity: float = Field(default=0.0, ge=0.0, le=1.0, description="Wave activity score (0-1)")
    calm_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Water calm score (0-1)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "shore_line_y": 670,
                "horizon_y": 3,
                "water_percentage": 75.0,
                "visibility": 0.85,
                "wave_activity": 0.3,
                "calm_score": 0.7
            }
        }


class AlertData(BaseModel):
    """Alert from intelligent alert engine"""
    alert_id: str = Field(..., description="Unique alert ID")
    swimmer_id: int = Field(..., description="Swimmer track ID")
    level: str = Field(..., description="Alert level: watch, alert, emergency")
    reason: str = Field(..., description="Alert reason")
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Risk score (0-100)")
    timestamp: float = Field(..., description="Alert timestamp")
    location: List[int] = Field(..., description="[x, y] position")
    zone: str = Field(..., description="Water zone")
    duration: float = Field(..., description="How long issue persisted (seconds)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Alert confidence (0-1)")
    context: str = Field(..., description="Human-readable context")
    action_recommended: str = Field(..., description="Action recommendation for lifeguard")
    acknowledged: bool = Field(default=False, description="Has lifeguard acknowledged?")
    
    class Config:
        json_schema_extra = {
            "example": {
                "alert_id": "ALERT-42-1-1674210000",
                "swimmer_id": 42,
                "level": "emergency",
                "reason": "drowning_behavior",
                "risk_score": 95.0,
                "timestamp": 1674210000.0,
                "location": [640, 360],
                "zone": "danger",
                "duration": 12.5,
                "confidence": 0.92,
                "context": "Swimmer #42 showing drowning behavior for 12 seconds in DANGER zone",
                "action_recommended": "🚨 IMMEDIATE WATER RESCUE - Drowning behavior detected",
                "acknowledged": False
            }
        }


class ProcessingMetrics(BaseModel):
    """Processing performance metrics for system health monitoring"""
    fps: float = Field(default=0.0, description="Current processing FPS")
    latency_ms: int = Field(default=0, description="Processing latency (milliseconds)")
    detections_raw: int = Field(default=0, description="Raw detections before filtering")
    detections_filtered: int = Field(default=0, description="Detections after filtering")
    active_tracks: int = Field(default=0, description="Currently active tracks")
    
    class Config:
        json_schema_extra = {
            "example": {
                "fps": 2.3,
                "latency_ms": 430,
                "detections_raw": 12,
                "detections_filtered": 8,
                "active_tracks": 8
            }
        }


class FrameResult(BaseModel):
    """
    Complete result for a single processed video frame.
    
    This is the MASTER SCHEMA used everywhere:
    - AI pipeline sends this via POST to backend
    - Backend stores this for playback
    - Backend broadcasts this via WebSocket
    - Frontend renders using this exact structure
    
    CRITICAL FIELDS for rendering:
    - video_width, video_height: Frontend MUST have these to scale boxes correctly
    - frame_index: For seeking/syncing
    - timestamp_ms: For precise video sync
    - swimmers[].bbox: In absolute video pixel coordinates
    """
    
    # Video identification
    video_id: str = Field(..., description="Unique video/upload ID")
    camera_id: str = Field(..., description="Camera ID (e.g., 'cam_001')")
    
    # Frame identification & timing
    frame_index: int = Field(..., ge=0, description="Frame number (0-based)")
    timestamp_ms: int = Field(..., ge=0, description="Video timestamp in milliseconds")
    
    # Video dimensions (CRITICAL for coordinate scaling)
    video_width: int = Field(..., gt=0, description="Video frame width (pixels)")
    video_height: int = Field(..., gt=0, description="Video frame height (pixels)")
    
    # Data
    swimmers: List[SwimmerData] = Field(default_factory=list, description="Detected swimmers")
    scene: SceneData = Field(default_factory=SceneData, description="Scene analysis data")
    metrics: ProcessingMetrics = Field(default_factory=ProcessingMetrics, description="Processing metrics")
    alerts: List[AlertData] = Field(default_factory=list, description="Active alerts from alert engine")
    
    # Metadata
    processed_at: datetime = Field(default_factory=datetime.utcnow, description="When this frame was processed")
    system_mode: str = Field(default="playback", description="System mode: playback or live")
    
    class Config:
        json_schema_extra = {
            "example": {
                "video_id": "video_123",
                "camera_id": "cam_001",
                "frame_index": 150,
                "timestamp_ms": 5000,
                "video_width": 1280,
                "video_height": 720,
                "swimmers": [
                    {
                        "track_id": 42,
                        "bbox": {"x": 100, "y": 200, "w": 80, "h": 150},
                        "confidence": 0.85,
                        "risk_score": 45,
                        "risk_level": "MEDIUM",
                        "behavior": "NORMAL",
                        "zone": "CAUTION",
                        "time_in_water": 120.5,
                        "distance_from_shore": 25.3,
                        "velocity": 12.5
                    }
                ],
                "scene": {
                    "shore_line_y": 670,
                    "horizon_y": 3,
                    "water_percentage": 75.0,
                    "visibility": 0.85,
                    "wave_activity": 0.3,
                    "calm_score": 0.7
                },
                "metrics": {
                    "fps": 2.3,
                    "latency_ms": 430,
                    "detections_raw": 12,
                    "detections_filtered": 8,
                    "active_tracks": 8
                },
                "processed_at": "2026-01-20T10:30:00Z",
                "system_mode": "playback"
            }
        }
    
    def to_websocket_message(self) -> Dict[str, Any]:
        """Convert to WebSocket message format (JSON-serializable)"""
        return self.model_dump(mode='json')
    
    @classmethod
    def from_legacy_swimmer_data(cls, legacy_data: Dict[str, Any]) -> "FrameResult":
        """
        Convert legacy swimmer data format to FrameResult.
        For backward compatibility during migration.
        """
        # Extract video dimensions from first swimmer if available
        video_width = legacy_data.get("video_width", 1280)
        video_height = legacy_data.get("video_height", 720)
        
        swimmers = []
        for s in legacy_data.get("swimmers", []):
            bbox = s.get("bbox", {})
            swimmers.append(SwimmerData(
                track_id=s.get("id", 0),
                bbox=BoundingBox(
                    x=bbox.get("x", 0),
                    y=bbox.get("y", 0),
                    w=bbox.get("w", 0),
                    h=bbox.get("h", 0)
                ),
                confidence=s.get("confidence", 0.0),
                risk_score=s.get("risk_score", 0),
                risk_level=s.get("risk_level", "LOW"),
                behavior=s.get("behavior", "NORMAL"),
                zone=s.get("zone", "SAFE"),
                time_in_water=s.get("time_in_water", 0.0),
                velocity=s.get("velocity", 0.0)
            ))
        
        return cls(
            video_id=legacy_data.get("video_id", "unknown"),
            camera_id=legacy_data.get("camera_id", "cam_001"),
            frame_index=legacy_data.get("frame_index", 0),
            timestamp_ms=legacy_data.get("timestamp_ms", 0),
            video_width=video_width,
            video_height=video_height,
            swimmers=swimmers,
            system_mode=legacy_data.get("system_mode", "playback")
        )
