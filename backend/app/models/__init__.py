"""
Models Package
==============
Export all Pydantic models for easy imports.

Usage:
    from app.models import SwimmerCreate, AlertResponse, etc.
"""

from app.models.swimmer import (
    SwimmerBase,
    SwimmerCreate,
    SwimmerUpdate,
    SwimmerInDB,
    SwimmerResponse,
    SwimmersListResponse,
    BoundingBox
)

from app.models.heatmap import (
    HeatmapBase,
    HeatmapCreate,
    HeatmapInDB,
    HeatmapResponse,
    HeatmapDataResponse,
    HeatmapData,
    HeatmapMetadata
)

from app.models.alert import (
    AlertBase,
    AlertCreate,
    AlertUpdate,
    AlertInDB,
    AlertResponse,
    AlertsListResponse,
    AlertType,
    AlertSeverity,
    AlertStatus
)

from app.models.camera import (
    CameraBase,
    CameraCreate,
    CameraUpdate,
    CameraInDB,
    CameraResponse,
    CamerasListResponse,
    CameraStatus,
    CameraLocation
)

__all__ = [
    # Swimmer models
    "SwimmerBase", "SwimmerCreate", "SwimmerUpdate", "SwimmerInDB",
    "SwimmerResponse", "SwimmersListResponse", "BoundingBox",
    
    # Heatmap models
    "HeatmapBase", "HeatmapCreate", "HeatmapInDB", "HeatmapResponse",
    "HeatmapDataResponse", "HeatmapData", "HeatmapMetadata",
    
    # Alert models
    "AlertBase", "AlertCreate", "AlertUpdate", "AlertInDB",
    "AlertResponse", "AlertsListResponse",
    "AlertType", "AlertSeverity", "AlertStatus",
    
    # Camera models
    "CameraBase", "CameraCreate", "CameraUpdate", "CameraInDB",
    "CameraResponse", "CamerasListResponse",
    "CameraStatus", "CameraLocation",
]


