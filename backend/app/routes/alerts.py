"""
Alert Routes
============
API endpoints for managing safety alerts.
"""

from fastapi import APIRouter, Query
from typing import Optional
import logging

from app.repositories import AlertRepository
from app.database import database
from app.models import AlertStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("")
async def get_alerts(
    camera_id: Optional[str] = Query(None, description="Filter by camera ID"),
    status: Optional[str] = Query(None, description="Filter by status (active, acknowledged, resolved)"),
    severity: Optional[str] = Query(None, description="Filter by severity (low, medium, high, critical)"),
    limit: int = Query(50, ge=1, le=100, description="Max number of alerts to return")
):
    """
    Get alerts with optional filters
    
    Query Parameters:
    - camera_id: Filter by specific camera
    - status: Filter by alert status
    - severity: Filter by severity level
    - limit: Max results (default 50, max 100)
    
    Returns:
    - List of alerts matching the filters
    """
    try:
        repo = AlertRepository(database.database)
        
        # Build filter dict
        status_filter = None
        if status:
            try:
                status_filter = AlertStatus(status)
            except ValueError:
                pass  # Invalid status, will return empty
        
        # Get alerts
        alerts = await repo.get_recent_alerts(
            camera_id=camera_id,
            status=status_filter,
            limit=limit
        )
        
        # Filter by severity if provided
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return {
            "success": True,
            "data": alerts,
            "count": len(alerts)
        }
        
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        return {
            "success": False,
            "data": [],
            "count": 0,
            "error": str(e)
        }


@router.get("/{alert_id}")
async def get_alert(alert_id: str):
    """
    Get a specific alert by ID
    
    Path Parameters:
    - alert_id: The alert ID to retrieve
    
    Returns:
    - Alert details if found, 404 if not found
    """
    try:
        repo = AlertRepository(database.database)
        # Find alert by alert_id
        alert_dict = await repo.collection.find_one({"alert_id": alert_id})
        if alert_dict:
            from app.models import AlertInDB
            alert = AlertInDB(**alert_dict)
        else:
            alert = None
        
        if alert:
            return {
                "success": True,
                "data": alert
            }
        else:
            return {
                "success": False,
                "data": None,
                "error": "Alert not found"
            }
    except Exception as e:
        logger.error(f"Error fetching alert {alert_id}: {e}")
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }


@router.patch("/{alert_id}")
async def update_alert(alert_id: str, update_data: dict):
    """
    Update an alert (e.g., acknowledge, resolve)
    
    Path Parameters:
    - alert_id: The alert ID to update
    
    Body:
    - status: New status (acknowledged, resolved, false_positive)
    - acknowledged_by: User who acknowledged
    - notes: Additional notes
    
    Returns:
    - Updated alert
    """
    try:
        from app.models import AlertUpdate
        repo = AlertRepository(database.database)
        alert_update = AlertUpdate(**update_data)
        updated_alert = await repo.update(alert_id, alert_update)
        
        if updated_alert:
            logger.info(f"Alert {alert_id} updated: {update_data}")
            return {
                "success": True,
                "data": updated_alert,
                "message": "Alert updated successfully"
            }
        else:
            return {
                "success": False,
                "data": None,
                "error": "Alert not found"
            }
    except Exception as e:
        logger.error(f"Error updating alert {alert_id}: {e}")
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }

