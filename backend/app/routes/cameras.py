"""
Camera Routes
=============
API endpoints for camera management.
"""

from fastapi import APIRouter
from typing import Optional
import logging

from app.repositories import CameraRepository
from app.database import database
from app.models.camera import CameraCreate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cameras", tags=["Cameras"])


@router.get("")
async def get_cameras(status: Optional[str] = None):
    """
    Get all cameras, optionally filtered by status
    
    Query Parameters:
    - status: Filter by camera status (active, inactive, maintenance)
    
    Returns:
    - List of cameras
    """
    try:
        repo = CameraRepository(database.database)
        
        cameras = await repo.get_all()
        
        # Filter by status if provided
        if status:
            cameras = [c for c in cameras if c.status == status]
        
        return {
            "success": True,
            "data": cameras,
            "count": len(cameras)
        }
        
    except Exception as e:
        logger.error(f"Error fetching cameras: {e}")
        return {
            "success": False,
            "data": [],
            "count": 0,
            "error": str(e)
        }


@router.get("/{camera_id}")
async def get_camera(camera_id: str):
    """
    Get a specific camera by ID
    
    Path Parameters:
    - camera_id: The camera ID to retrieve
    
    Returns:
    - Camera details if found
    """
    try:
        repo = CameraRepository(database.database)
        camera = await repo.get_by_id(camera_id)
        
        if camera:
            return {
                "success": True,
                "data": camera
            }
        else:
            return {
                "success": False,
                "data": None,
                "error": "Camera not found"
            }
    except Exception as e:
        logger.error(f"Error fetching camera {camera_id}: {e}")
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }


@router.post("")
async def register_camera(camera: CameraCreate):
    """
    Register a new camera
    
    Body:
    - camera_id: Unique camera identifier
    - name: Human-readable camera name
    - location: Camera location details
    - status: Camera status (default: active)
    
    Returns:
    - Created camera
    """
    try:
        repo = CameraRepository(database.database)
        created_camera = await repo.create(camera)
        
        logger.info(f"Camera registered: {camera.camera_id}")
        return {
            "success": True,
            "data": created_camera,
            "message": "Camera registered successfully"
        }
        
    except Exception as e:
        logger.error(f"Error registering camera: {e}")
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }


@router.patch("/{camera_id}")
async def update_camera(camera_id: str, update_data: dict):
    """
    Update camera configuration
    
    Path Parameters:
    - camera_id: The camera ID to update
    
    Body:
    - name: New camera name
    - status: New status
    - location: Updated location
    
    Returns:
    - Updated camera
    """
    try:
        from app.models import CameraUpdate
        repo = CameraRepository(database.database)
        camera_update = CameraUpdate(**update_data)
        updated_camera = await repo.update(camera_id, camera_update)
        
        if updated_camera:
            logger.info(f"Camera {camera_id} updated")
            return {
                "success": True,
                "data": updated_camera,
                "message": "Camera updated successfully"
            }
        else:
            return {
                "success": False,
                "data": None,
                "error": "Camera not found"
            }
    except Exception as e:
        logger.error(f"Error updating camera {camera_id}: {e}")
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }

