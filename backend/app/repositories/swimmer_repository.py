"""
Swimmer Repository
==================
Database access layer for swimmer tracking data.

Why Repository Pattern?
- Separates database logic from business logic
- Makes code testable (can mock repository)
- Centralizes database queries
- Easy to switch databases if needed

All methods are async for non-blocking I/O.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models import SwimmerCreate, SwimmerUpdate, SwimmerInDB
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class SwimmerRepository:
    """
    Database operations for swimmer tracking
    
    Handles CRUD (Create, Read, Update, Delete) operations for swimmers.
    """
    
    def __init__(self, database: AsyncIOMotorDatabase):
        """
        Initialize repository with database connection
        
        Args:
            database: MongoDB database instance
        """
        self.collection = database.swimmers
    
    async def create(self, swimmer: SwimmerCreate) -> SwimmerInDB:
        """
        Create a new swimmer record
        
        Args:
            swimmer: Swimmer data from AI pipeline
            
        Returns:
            Created swimmer with timestamps
        """
        now = datetime.utcnow()
        
        swimmer_dict = {
            **swimmer.model_dump(),
            "first_seen": now,
            "last_seen": now,
            "status": "active",
            "created_at": now,
            "updated_at": now
        }
        
        try:
            result = await self.collection.insert_one(swimmer_dict)
            swimmer_dict["_id"] = result.inserted_id
            logger.debug(f"Created swimmer: camera={swimmer.camera_id}, track={swimmer.track_id}")
            return SwimmerInDB(**swimmer_dict)
        except Exception as e:
            logger.error(f"Error creating swimmer: {e}")
            raise
    
    async def get_by_track_id(self, camera_id: str, track_id: int) -> Optional[SwimmerInDB]:
        """
        Get swimmer by camera and track ID
        
        Args:
            camera_id: Camera identifier
            track_id: Swimmer track ID
            
        Returns:
            Swimmer if found, None otherwise
        """
        swimmer_dict = await self.collection.find_one({
            "camera_id": camera_id,
            "track_id": track_id
        })
        
        if swimmer_dict:
            return SwimmerInDB(**swimmer_dict)
        return None
    
    async def update(self, camera_id: str, track_id: int, update_data: SwimmerUpdate) -> Optional[SwimmerInDB]:
        """
        Update existing swimmer record
        
        Args:
            camera_id: Camera identifier
            track_id: Swimmer track ID
            update_data: Fields to update
            
        Returns:
            Updated swimmer if found, None otherwise
        """
        update_dict = update_data.model_dump(exclude_unset=True)
        update_dict["updated_at"] = datetime.utcnow()
        
        result = await self.collection.find_one_and_update(
            {"camera_id": camera_id, "track_id": track_id},
            {"$set": update_dict},
            return_document=True  # Return updated document
        )
        
        if result:
            logger.debug(f"Updated swimmer: camera={camera_id}, track={track_id}")
            return SwimmerInDB(**result)
        return None
    
    async def upsert(self, swimmer: SwimmerCreate) -> SwimmerInDB:
        """
        Update if exists, create if not (upsert)
        
        Used when receiving data from AI pipeline.
        Updates last_seen and bbox if swimmer exists.
        
        Args:
            swimmer: Swimmer data from AI pipeline
            
        Returns:
            Updated or created swimmer
        """
        now = datetime.utcnow()
        
        # Try to find existing swimmer
        existing = await self.get_by_track_id(swimmer.camera_id, swimmer.track_id)
        
        if existing:
            # Update existing swimmer
            update_data = SwimmerUpdate(
                bbox=swimmer.bbox,
                confidence=swimmer.confidence,
                last_seen=now,
                status="active"  # Mark as active (seen recently)
            )
            return await self.update(swimmer.camera_id, swimmer.track_id, update_data)
        else:
            # Create new swimmer
            return await self.create(swimmer)
    
    async def get_active_swimmers(self, camera_id: Optional[str] = None, limit: int = 100) -> List[SwimmerInDB]:
        """
        Get all active swimmers
        
        Active = status is 'active' and seen within threshold time.
        
        Args:
            camera_id: Filter by camera (optional)
            limit: Maximum number of swimmers to return
            
        Returns:
            List of active swimmers
        """
        # Calculate cutoff time
        cutoff_time = datetime.utcnow() - timedelta(seconds=settings.SWIMMER_INACTIVE_THRESHOLD)
        
        # Build query filter
        query = {
            "status": "active",
            "last_seen": {"$gte": cutoff_time}
        }
        
        if camera_id:
            query["camera_id"] = camera_id
        
        # Execute query
        cursor = self.collection.find(query).limit(limit)
        swimmers = await cursor.to_list(length=limit)
        
        return [SwimmerInDB(**s) for s in swimmers]
    
    async def mark_inactive(self, camera_id: str, threshold_seconds: Optional[int] = None) -> int:
        """
        Mark swimmers as inactive if not seen recently
        
        Args:
            camera_id: Camera to check
            threshold_seconds: Override default threshold
            
        Returns:
            Number of swimmers marked inactive
        """
        threshold = threshold_seconds or settings.SWIMMER_INACTIVE_THRESHOLD
        cutoff_time = datetime.utcnow() - timedelta(seconds=threshold)
        
        result = await self.collection.update_many(
            {
                "camera_id": camera_id,
                "status": "active",
                "last_seen": {"$lt": cutoff_time}
            },
            {
                "$set": {
                    "status": "inactive",
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"Marked {result.modified_count} swimmers as inactive for camera {camera_id}")
        
        return result.modified_count
    
    async def delete_old_swimmers(self, days_old: int = 7) -> int:
        """
        Delete old inactive swimmers (cleanup)
        
        Args:
            days_old: Delete swimmers inactive for this many days
            
        Returns:
            Number of swimmers deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        result = await self.collection.delete_many({
            "status": "inactive",
            "last_seen": {"$lt": cutoff_date}
        })
        
        if result.deleted_count > 0:
            logger.info(f"Deleted {result.deleted_count} old inactive swimmers")
        
        return result.deleted_count

