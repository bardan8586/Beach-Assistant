"""
Camera Data Models
==================
Pydantic models for camera management.

Supports multiple cameras for scalable deployment.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class CameraStatus(str, Enum):
    """Camera operational status"""
    ACTIVE = "active"          # Camera is online and streaming
    INACTIVE = "inactive"      # Camera is offline
    MAINTENANCE = "maintenance" # Camera under maintenance


class CameraLocation(BaseModel):
    """
    Physical location of the camera
    """
    beach: str = Field(..., description="Beach name")
    lat: Optional[float] = Field(None, description="Latitude")
    lng: Optional[float] = Field(None, description="Longitude")
    description: Optional[str] = Field(None, description="Location details")


class CameraBase(BaseModel):
    """Base camera data"""
    camera_id: str = Field(..., description="Unique camera identifier")
    name: str = Field(..., description="Human-readable camera name")
    location: CameraLocation


class CameraCreate(CameraBase):
    """
    Data required to register a new camera
    """
    rtsp_url: Optional[str] = Field(None, description="RTSP stream URL (stored encrypted)")
    status: CameraStatus = CameraStatus.ACTIVE


class CameraUpdate(BaseModel):
    """
    Data for updating camera configuration
    """
    name: Optional[str] = None
    location: Optional[CameraLocation] = None
    status: Optional[CameraStatus] = None
    rtsp_url: Optional[str] = None


class CameraInDB(CameraBase):
    """
    Complete camera record as stored in MongoDB
    """
    rtsp_url: Optional[str] = Field(None, description="RTSP stream URL (encrypted)")
    status: CameraStatus = CameraStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen: Optional[datetime] = Field(None, description="Last data received")
    
    class Config:
        from_attributes = True


class CameraResponse(BaseModel):
    """
    Camera data returned by API
    
    RTSP URL is excluded for security (not exposed to frontend).
    """
    camera_id: str
    name: str
    location: CameraLocation
    status: CameraStatus
    created_at: datetime
    last_seen: Optional[datetime] = None


class CamerasListResponse(BaseModel):
    """
    API response for list of cameras
    """
    success: bool = True
    data: list[CameraResponse]
    count: int
    message: Optional[str] = None

