"""
Camera Repository
=================
Database access layer for camera management.
"""

from typing import List, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models import CameraCreate, CameraUpdate, CameraInDB
import logging

logger = logging.getLogger(__name__)


class CameraRepository:
    """Database operations for cameras"""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.collection = database.cameras
    
    async def create(self, camera: CameraCreate) -> CameraInDB:
        """Register new camera"""
        now = datetime.utcnow()
        
        camera_dict = {
            **camera.model_dump(),
            "created_at": now,
            "updated_at": now
        }
        
        result = await self.collection.insert_one(camera_dict)
        camera_dict["_id"] = result.inserted_id
        
        logger.info(f"Registered camera: {camera.camera_id}")
        return CameraInDB(**camera_dict)
    
    async def get_by_id(self, camera_id: str) -> Optional[CameraInDB]:
        """Get camera by ID"""
        camera_dict = await self.collection.find_one({"camera_id": camera_id})
        
        if camera_dict:
            return CameraInDB(**camera_dict)
        return None
    
    async def update(self, camera_id: str, update_data: CameraUpdate) -> Optional[CameraInDB]:
        """Update camera configuration"""
        update_dict = update_data.model_dump(exclude_unset=True)
        update_dict["updated_at"] = datetime.utcnow()
        
        result = await self.collection.find_one_and_update(
            {"camera_id": camera_id},
            {"$set": update_dict},
            return_document=True
        )
        
        if result:
            return CameraInDB(**result)
        return None
    
    async def get_all(self) -> List[CameraInDB]:
        """Get all cameras"""
        cursor = self.collection.find()
        cameras = await cursor.to_list(length=None)
        
        return [CameraInDB(**c) for c in cameras]
    
    async def update_last_seen(self, camera_id: str):
        """Update camera's last_seen timestamp"""
        await self.collection.update_one(
            {"camera_id": camera_id},
            {"$set": {"last_seen": datetime.utcnow()}}
        )

