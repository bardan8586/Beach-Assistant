"""
Swimmers API Routes
===================
REST endpoints for swimmer tracking data.
"""

from fastapi import APIRouter, Query
from app.models import SwimmersListResponse
from app.services import swimmer_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/swimmers", tags=["swimmers"])


@router.get("", response_model=SwimmersListResponse)
async def get_swimmers(
    camera_id: str = Query(None, description="Filter by camera ID"),
    status: str = Query("active", description="Filter by status (active/inactive)"),
    limit: int = Query(100, ge=1, le=500, description="Maximum swimmers to return")
):
    """
    Get current swimmers
    
    Returns list of active or inactive swimmers with optional camera filter.
    """
    try:
        if status == "active":
            swimmers = await swimmer_service.get_active_swimmers(camera_id, limit)
        else:
            # For inactive swimmers, would need additional service method
            swimmers = []
        
        return SwimmersListResponse(
            success=True,
            data=swimmers,
            count=len(swimmers)
        )
    except Exception as e:
        logger.error(f"Error fetching swimmers: {e}")
        return SwimmersListResponse(
            success=False,
            data=[],
            count=0,
            message=f"Error: {str(e)}"
        )

