"""
Alert Repository
================
Database access layer for safety alerts.
"""

from typing import List, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models import AlertCreate, AlertUpdate, AlertInDB, AlertStatus
import uuid
import logging

logger = logging.getLogger(__name__)


class AlertRepository:
    """Database operations for alerts"""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.collection = database.alerts
    
    async def create(self, alert: AlertCreate) -> AlertInDB:
        """Create new alert"""
        now = datetime.utcnow()
        alert_id = f"alert_{uuid.uuid4().hex[:12]}"
        
        alert_dict = {
            "alert_id": alert_id,
            **alert.model_dump(),
            "timestamp": now,
            "status": AlertStatus.ACTIVE,
            "created_at": now,
            "updated_at": now
        }
        
        result = await self.collection.insert_one(alert_dict)
        alert_dict["_id"] = result.inserted_id
        
        logger.info(f"Created alert: {alert_id} for track {alert.track_id}")
        return AlertInDB(**alert_dict)
    
    async def update(self, alert_id: str, update_data: AlertUpdate) -> Optional[AlertInDB]:
        """Update alert (acknowledge/resolve)"""
        update_dict = update_data.model_dump(exclude_unset=True)
        update_dict["updated_at"] = datetime.utcnow()
        
        # Set timestamps based on status change
        if update_data.status == AlertStatus.ACKNOWLEDGED:
            update_dict["acknowledged_at"] = datetime.utcnow()
        elif update_data.status == AlertStatus.RESOLVED:
            update_dict["resolved_at"] = datetime.utcnow()
        
        result = await self.collection.find_one_and_update(
            {"alert_id": alert_id},
            {"$set": update_dict},
            return_document=True
        )
        
        if result:
            return AlertInDB(**result)
        return None
    
    async def get_recent_alerts(
        self,
        camera_id: Optional[str] = None,
        status: Optional[AlertStatus] = None,
        limit: int = 50
    ) -> List[AlertInDB]:
        """Get recent alerts with filters"""
        query = {}
        
        if camera_id:
            query["camera_id"] = camera_id
        if status:
            query["status"] = status
        
        cursor = self.collection.find(query).sort("timestamp", -1).limit(limit)
        alerts = await cursor.to_list(length=limit)
        
        return [AlertInDB(**a) for a in alerts]

