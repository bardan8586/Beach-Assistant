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
from app.models import FrameResult
from app.utils import results_storage
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data", tags=["ingestion"])


# Legacy request format (for backward compatibility)
class IngestRequest(BaseModel):
    """Request body for AI pipeline data (LEGACY - use FrameResult instead)"""
    camera_id: str
    timestamp: float
    swimmers: List[dict]  # List of {track_id, bbox, confidence}
    heatmap: Optional[dict] = None  # Optional heatmap data


@router.post("/ingest")
async def ingest_data(frame_result: FrameResult):
    """
    Receive FrameResult from AI pipeline
    
    This endpoint is called by the AI main.py script to send complete frame analysis:
    - Video dimensions (for coordinate scaling)
    - Frame index and timestamp (for sync)
    - Swimmer detections with bounding boxes, risk, behavior
    - Scene analysis (shore, horizon, water conditions)
    - Processing metrics
    
    The data is:
    1. Validated against FrameResult schema
    2. Stored to results.jsonl for playback
    3. Broadcast via WebSocket to connected clients (for real-time display)
    """
    try:
        # Store frame result for playback (Task 1.2)
        try:
            results_storage.write_frame_result(
                video_id=frame_result.video_id,
                frame_result=frame_result.model_dump()  # Convert Pydantic model to dict
            )
            if frame_result.frame_index % 30 == 0:
                logger.debug(f"✅ Saved frame {frame_result.frame_index} to storage")
        except Exception as e:
            logger.error(f"❌ Failed to store frame result for video_id={frame_result.video_id}: {e}", exc_info=True)
        
        # Update camera last_seen
        if database.database is not None:
            try:
                camera_repo = CameraRepository(database.database)
                await camera_repo.update_last_seen(frame_result.camera_id)
            except Exception as e:
                logger.warning(f"Failed to update camera last_seen: {e}")
        
        # Broadcast FrameResult to WebSocket clients (entire frame result)
        await websocket_service.broadcast_frame_result(
            camera_id=frame_result.camera_id,
            frame_result=frame_result.model_dump()  # Convert Pydantic model to dict
        )
        
        logger.info(
            f"Ingested FrameResult: camera={frame_result.camera_id}, "
            f"frame={frame_result.frame_index}, swimmers={len(frame_result.swimmers)}, "
            f"dims={frame_result.video_width}x{frame_result.video_height}"
        )
        
        return {
            "success": True,
            "message": f"Processed frame {frame_result.frame_index} with {len(frame_result.swimmers)} swimmers",
            "camera_id": frame_result.camera_id,
            "frame_index": frame_result.frame_index,
            "video_dimensions": {
                "width": frame_result.video_width,
                "height": frame_result.video_height
            }
        }
        
    except Exception as e:
        logger.error(f"Error ingesting FrameResult: {e}")
        raise HTTPException(status_code=500, detail=str(e))

