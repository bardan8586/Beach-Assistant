"""
WebSocket Service
=================
Manages WebSocket connections and broadcasts real-time updates.

Responsibilities:
- Track active WebSocket connections
- Broadcast updates to connected clients
- Handle client subscriptions (per-camera filtering)
"""

from fastapi import WebSocket
from typing import Dict, Set
import json
import logging

logger = logging.getLogger(__name__)


class WebSocketService:
    """
    Manages WebSocket connections for real-time updates
    
    Supports multiple concurrent connections with per-camera filtering.
    """
    
    def __init__(self):
        """Initialize connection manager"""
        # Map of camera_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, camera_id: str = "all"):
        """
        Register new WebSocket connection
        
        Args:
            websocket: WebSocket connection
            camera_id: Camera to subscribe to (default: "all")
        """
        await websocket.accept()
        
        if camera_id not in self.active_connections:
            self.active_connections[camera_id] = set()
        
        self.active_connections[camera_id].add(websocket)
        logger.info(f"WebSocket connected: camera={camera_id}, total={len(self.active_connections[camera_id])}")
    
    def disconnect(self, websocket: WebSocket, camera_id: str = "all"):
        """
        Remove WebSocket connection
        
        Args:
            websocket: WebSocket connection to remove
            camera_id: Camera subscription
        """
        if camera_id in self.active_connections:
            self.active_connections[camera_id].discard(websocket)
            
            # Clean up empty sets
            if len(self.active_connections[camera_id]) == 0:
                del self.active_connections[camera_id]
        
        logger.info(f"WebSocket disconnected: camera={camera_id}")
    
    async def broadcast_to_camera(self, camera_id: str, message: dict):
        """
        Broadcast message to all clients subscribed to a camera
        
        Args:
            camera_id: Camera to broadcast to
            message: JSON-serializable message
        """
        # Get connections for this camera
        connections = self.active_connections.get(camera_id, set())
        
        # Also broadcast to "all" subscribers
        all_connections = self.active_connections.get("all", set())
        
        target_connections = connections | all_connections
        
        if not target_connections:
            return  # No one listening
        
        # Serialize message once
        message_json = json.dumps(message)
        
        # Broadcast to all connections
        disconnected = []
        for websocket in target_connections:
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected websockets
        for ws in disconnected:
            self.disconnect(ws, camera_id)
    
    async def broadcast_swimmer_update(self, camera_id: str, swimmers: list):
        """
        Broadcast swimmer position update
        
        Args:
            camera_id: Camera identifier
            swimmers: List of swimmer data
        """
        message = {
            "type": "update",
            "camera_id": camera_id,
            "data": {
                "swimmers": swimmers,
                "swimmer_count": len(swimmers)
            }
        }
        await self.broadcast_to_camera(camera_id, message)
    
    async def broadcast_alert(self, camera_id: str, alert: dict):
        """
        Broadcast new alert
        
        Args:
            camera_id: Camera identifier
            alert: Alert data
        """
        message = {
            "type": "alert",
            "camera_id": camera_id,
            "data": alert
        }
        await self.broadcast_to_camera(camera_id, message)


# Global WebSocket service instance
websocket_service = WebSocketService()

