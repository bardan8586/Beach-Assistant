"""
Routes Package
==============
Export all API routers.
"""

from app.routes.swimmers import router as swimmers_router
from app.routes.ingest import router as ingest_router
from app.routes.websocket import router as websocket_router
from app.routes.alerts import router as alerts_router
from app.routes.cameras import router as cameras_router
from app.routes.video import router as video_router

__all__ = [
    "swimmers_router",
    "ingest_router",
    "websocket_router",
    "alerts_router",
    "cameras_router",
    "video_router",
]
