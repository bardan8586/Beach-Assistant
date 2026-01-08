"""
Heatmap Repository
==================
Database access layer for heatmap data.
"""

from typing import Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models import HeatmapCreate, HeatmapInDB
import logging

logger = logging.getLogger(__name__)


class HeatmapRepository:
    """Database operations for heatmap visualization"""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.collection = database.heatmaps
    
    async def create(self, heatmap: HeatmapCreate) -> HeatmapInDB:
        """Create/update heatmap (keeps only latest per camera)"""
        now = datetime.utcnow()
        
        heatmap_dict = {
            **heatmap.model_dump(),
            "created_at": now
        }
        
        # Replace existing heatmap for this camera (keep only latest)
        await self.collection.delete_many({"camera_id": heatmap.camera_id})
        
        result = await self.collection.insert_one(heatmap_dict)
        heatmap_dict["_id"] = result.inserted_id
        
        logger.debug(f"Saved heatmap for camera {heatmap.camera_id}")
        return HeatmapInDB(**heatmap_dict)
    
    async def get_latest(self, camera_id: str) -> Optional[HeatmapInDB]:
        """Get most recent heatmap for a camera"""
        heatmap_dict = await self.collection.find_one(
            {"camera_id": camera_id},
            sort=[("timestamp", -1)]
        )
        
        if heatmap_dict:
            return HeatmapInDB(**heatmap_dict)
        return None


