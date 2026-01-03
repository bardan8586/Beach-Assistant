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
    try:
        # Accept the WebSocket connection first
        await websocket.accept()
        logger.info(f"✅ WebSocket connection accepted for camera: {camera_id}")
        
        # Register with service (don't call accept again, already accepted)
        if camera_id not in websocket_service.active_connections:
            websocket_service.active_connections[camera_id] = set()
        websocket_service.active_connections[camera_id].add(websocket)
        logger.info(f"✅ WebSocket registered: camera={camera_id}, total={len(websocket_service.active_connections[camera_id])}")
        
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "message": f"Subscribed to camera: {camera_id}",
            "camera_id": camera_id
        })
        logger.info(f"✅ Sent connection confirmation to camera: {camera_id}")
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive messages from client (e.g., heartbeat pings)
                data = await websocket.receive_text()
                
                # Echo back (heartbeat response)
                if data == "ping":
                    await websocket.send_text("pong")
            except WebSocketDisconnect:
                logger.info(f"Client disconnected from camera {camera_id}")
                break
            except Exception as e:
                # If receive fails, connection might be closed
                logger.debug(f"WebSocket receive error: {e}")
                break
            
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from camera {camera_id}")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}", exc_info=True)
    finally:
        # Clean up connection
        if camera_id in websocket_service.active_connections:
            websocket_service.active_connections[camera_id].discard(websocket)
            if len(websocket_service.active_connections[camera_id]) == 0:
                del websocket_service.active_connections[camera_id]
        logger.info(f"✅ WebSocket cleaned up for camera: {camera_id}")

