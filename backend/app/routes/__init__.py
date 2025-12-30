"""
Routes Package
==============
Export all API routers.
"""

from app.routes.swimmers import router as swimmers_router
from app.routes.ingest import router as ingest_router
from app.routes.websocket import router as websocket_router

__all__ = [
    "swimmers_router",
    "ingest_router",
    "websocket_router",
]

