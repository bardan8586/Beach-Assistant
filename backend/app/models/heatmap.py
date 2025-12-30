"""
Heatmap Data Models
====================
Pydantic models for heatmap visualization data.

Heatmap represents swimmer activity density over time.
Stored as 2D array or base64-encoded image.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class HeatmapMetadata(BaseModel):
    """
    Heatmap generation parameters
    
    Stores settings used to generate the heatmap.
    """
    width: int = Field(..., description="Heatmap width in pixels")
    height: int = Field(..., description="Heatmap height in pixels")
    decay: float = Field(default=0.98, description="Temporal decay factor (0-1)")
    gauss_sigma: int = Field(default=12, description="Gaussian blur sigma")


class HeatmapData(BaseModel):
    """
    Heatmap pixel data
    
    Can be stored as:
    - 2D array of floats (values)
    - Base64-encoded image string
    """
    values: Optional[List[List[float]]] = Field(None, description="2D array of heatmap values")
    image_base64: Optional[str] = Field(None, description="Base64-encoded heatmap image")


class HeatmapBase(BaseModel):
    """Base heatmap data"""
    camera_id: str = Field(..., description="Camera identifier")
    timestamp: datetime = Field(..., description="Heatmap generation timestamp")
    metadata: HeatmapMetadata


class HeatmapCreate(HeatmapBase):
    """
    Data required to create a new heatmap
    
    Received from AI pipeline.
    """
    data: HeatmapData


class HeatmapInDB(HeatmapBase):
    """
    Complete heatmap record as stored in MongoDB
    """
    data: HeatmapData
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True


class HeatmapResponse(BaseModel):
    """
    Heatmap data returned by API
    
    Simplified response with image URL instead of raw data.
    """
    camera_id: str
    timestamp: datetime
    image_url: str = Field(..., description="URL to fetch heatmap image")
    metadata: HeatmapMetadata


class HeatmapDataResponse(BaseModel):
    """
    API response for heatmap data
    """
    success: bool = True
    data: HeatmapResponse
    message: Optional[str] = None

