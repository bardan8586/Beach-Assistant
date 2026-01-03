"""
Data Ingestion API
==================
Endpoint for receiving data from AI pipeline.

This is the main integration point between AI and backend.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.services import swimmer_service, websocket_service
from app.repositories import CameraRepository
from app.database import database
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data", tags=["ingestion"])


class IngestRequest(BaseModel):
    """Request body for AI pipeline data"""
    camera_id: str
    timestamp: float
    swimmers: List[dict]  # List of {track_id, bbox, confidence}
    heatmap: Optional[dict] = None  # Optional heatmap data


@router.post("/ingest")
async def ingest_data(request: IngestRequest):
    """
    Receive data from AI pipeline
    
    This endpoint is called by the AI main.py script to send:
    - Swimmer detections with bounding boxes
    - Heatmap data (optional)
    - Frame timestamp
    
    The data is:
    1. Stored in MongoDB
    2. Broadcast via WebSocket to connected clients
    """
    try:
        # Update camera last_seen
        if database.database is not None:
            try:
                camera_repo = CameraRepository(database.database)
                await camera_repo.update_last_seen(request.camera_id)
            except Exception as e:
                logger.warning(f"Failed to update camera last_seen: {e}")
        
        # Process swimmer detections
        swimmers = await swimmer_service.process_detections(
            camera_id=request.camera_id,
            swimmers=request.swimmers,
            timestamp=request.timestamp
        )
        
        # Broadcast to WebSocket clients
        await websocket_service.broadcast_swimmer_update(
            camera_id=request.camera_id,
            swimmers=[s.model_dump() for s in swimmers],
            timestamp=request.timestamp  # Pass timestamp from AI pipeline
        )
        
        logger.info(f"Ingested data: camera={request.camera_id}, swimmers={len(swimmers)}")
        
        return {
            "success": True,
            "message": f"Processed {len(swimmers)} swimmers",
            "camera_id": request.camera_id
        }
        
    except Exception as e:
        logger.error(f"Error ingesting data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

