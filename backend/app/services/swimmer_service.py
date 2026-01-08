"""
Swimmer Service
===============
Business logic for processing swimmer data from AI pipeline.

Responsibilities:
- Receive swimmer detections from AI
- Update/create swimmer records
- Mark inactive swimmers
- Trigger WebSocket broadcasts
"""

from typing import List
from app.repositories import SwimmerRepository
from app.models import SwimmerCreate, SwimmerResponse
from app.database import database
import logging

logger = logging.getLogger(__name__)


class SwimmerService:
    """
    Service for processing swimmer tracking data
    
    Handles the business logic between AI pipeline and database.
    """
    
    def __init__(self):
        """Initialize service (repository created on demand)"""
        self._repository = None
    
    @property
    def repository(self) -> SwimmerRepository:
        """Lazy-load repository"""
        if self._repository is None:
            self._repository = SwimmerRepository(database.get_database())
        return self._repository
    
    async def process_detections(
        self,
        camera_id: str,
        swimmers: List[dict],
        timestamp: float
    ) -> List[SwimmerResponse]:
        """
        Process swimmer detections from AI pipeline
        
        Args:
            camera_id: Camera identifier
            swimmers: List of swimmer detections with bbox and confidence
            timestamp: Frame timestamp
            
        Returns:
            List of processed swimmers
        """
        processed_swimmers = []
        
        for swimmer_data in swimmers:
            try:
                # Create SwimmerCreate model from AI data
                swimmer = SwimmerCreate(
                    camera_id=camera_id,
                    track_id=swimmer_data["track_id"],
                    bbox=swimmer_data["bbox"],
                    confidence=swimmer_data["confidence"]
                )
                
                # Upsert to database (update if exists, create if not)
                db_swimmer = await self.repository.upsert(swimmer)
                processed_swimmers.append(SwimmerResponse(**db_swimmer.model_dump()))
                
            except Exception as e:
                logger.error(f"Error processing swimmer {swimmer_data.get('track_id')}: {e}")
        
        # Mark swimmers not seen recently as inactive
        await self.repository.mark_inactive(camera_id)
        
        logger.info(f"Processed {len(processed_swimmers)} swimmers for camera {camera_id}")
        return processed_swimmers
    
    async def get_active_swimmers(
        self,
        camera_id: str = None,
        limit: int = 100
    ) -> List[SwimmerResponse]:
        """
        Get currently active swimmers
        
        Args:
            camera_id: Filter by camera (optional)
            limit: Maximum swimmers to return
            
        Returns:
            List of active swimmers
        """
        swimmers = await self.repository.get_active_swimmers(camera_id, limit)
        return [SwimmerResponse(**s.model_dump()) for s in swimmers]


# Global service instance
swimmer_service = SwimmerService()


