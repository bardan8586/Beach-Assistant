"""
FastAPI Main Application
=========================
Backend server for Beach Safety Monitor.

This is the entry point for the backend API server.
It initializes FastAPI, connects to MongoDB, and registers all routes.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import database
from app.routes import swimmers_router, ingest_router, websocket_router, alerts_router, cameras_router, video_router
from app.utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    
    Handles startup and shutdown:
    - Startup: Connect to MongoDB, initialize services
    - Shutdown: Close database connections
    """
    # Startup
    logger.info("🚀 Starting Beach Safety Monitor Backend...")
    
    try:
        # Connect to MongoDB (non-blocking, won't fail if connection fails)
        try:
            await database.connect()
            logger.info("✓ MongoDB connected")
        except Exception as e:
            logger.warning(f"⚠ MongoDB connection failed (continuing anyway): {e}")
            logger.warning("⚠ API will work but database operations will fail")
        
        yield  # Application runs here
        
    finally:
        # Shutdown
        logger.info("🛑 Shutting down Beach Safety Monitor Backend...")
        await database.disconnect()
        logger.info("✓ MongoDB disconnected")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Backend API for real-time beach safety monitoring with AI",
    lifespan=lifespan
)


# Configure CORS (allow frontend to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log 422 validation errors (e.g. ingest payload mismatch) so we can fix schema."""
    logger.warning(
        "Validation error on %s %s: %s",
        request.method,
        request.url.path,
        exc.errors(),
    )
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


# Register API routes
app.include_router(swimmers_router, prefix=settings.API_PREFIX)
app.include_router(ingest_router, prefix=settings.API_PREFIX)
app.include_router(alerts_router, prefix=settings.API_PREFIX)
app.include_router(cameras_router, prefix=settings.API_PREFIX)
app.include_router(video_router, prefix=settings.API_PREFIX)  # Video upload & processing
app.include_router(websocket_router)  # WebSocket doesn't use /api prefix


@app.get("/")
async def root():
    """
    Root endpoint - API health check
    
    Returns basic info about the API.
    """
    return {
        "message": "Beach Safety Monitor API",
        "version": "1.0.0",
        "status": "online",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    
    Used by load balancers and monitoring tools.
    """
    try:
        db_status = "connected" if database.database is not None else "disconnected"
    except Exception:
        db_status = "unknown"
    
    return {
        "status": "healthy",
        "database": db_status
    }


if __name__ == "__main__":
    import uvicorn
    
    # Run server with WebSocket support
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,  # Auto-reload on code changes in debug mode
        log_level="info",
        ws="auto"  # Enable WebSocket support
    )

