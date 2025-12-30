"""
WebSocket Endpoint
==================
Real-time updates for dashboard.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.services import websocket_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/feed")
async def websocket_feed(
    websocket: WebSocket,
    camera_id: str = Query("all", description="Camera to subscribe to")
):
    """
    WebSocket endpoint for real-time updates
    
    Client receives:
    - Swimmer position updates
    - New alerts
    - Heatmap refresh notifications
    
    Connection URL examples:
    - ws://localhost:8000/ws/feed?camera_id=cam_001
    - ws://localhost:8000/ws/feed (subscribe to all cameras)
    """
    await websocket_service.connect(websocket, camera_id)
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "message": f"Subscribed to camera: {camera_id}"
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            # Receive messages from client (e.g., heartbeat pings)
            data = await websocket.receive_text()
            
            # Echo back (heartbeat response)
            if data == "ping":
                await websocket.send_text("pong")
            
    except WebSocketDisconnect:
        websocket_service.disconnect(websocket, camera_id)
        logger.info(f"Client disconnected from camera {camera_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_service.disconnect(websocket, camera_id)

