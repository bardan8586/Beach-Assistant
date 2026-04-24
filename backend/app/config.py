"""
Configuration Module
====================
Manages all application settings using Pydantic Settings.
Environment variables are loaded from .env file.

Why Pydantic Settings?
- Type validation at startup
- Environment variable management
- Default values with overrides
- Automatic .env file loading
"""

from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    """
    Application Settings
    
    All settings can be overridden via environment variables.
    Example: Set MONGODB_URL="mongodb://..." in .env file
    """
    
    # -------------------- MongoDB Configuration --------------------
    MONGODB_URL: str = "mongodb://localhost:27017"  # Override with MongoDB Atlas URL
    DATABASE_NAME: str = "beach_safety"
    
    # -------------------- API Configuration --------------------
    API_PREFIX: str = "/api"
    API_VERSION: str = "v1"
    PROJECT_NAME: str = "Beach Safety Monitor"
    
    # -------------------- CORS Configuration --------------------
    # Allow frontend to connect from these origins (Vite may use 5173, 5174, 5175, etc.)
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:5176",
    ]
    
    # -------------------- WebSocket Configuration --------------------
    WS_HEARTBEAT_INTERVAL: int = 30  # seconds between heartbeat pings
    WS_MESSAGE_MAX_SIZE: int = 10 * 1024 * 1024  # 10MB max message size
    
    # -------------------- Data Retention Configuration --------------------
    # How long before marking a swimmer as inactive?
    SWIMMER_INACTIVE_THRESHOLD: int = 10  # seconds
    
    # How long to keep heatmap snapshots?
    HEATMAP_RETENTION_HOURS: int = 24  # hours
    
    # How long to keep old alerts?
    ALERT_RETENTION_DAYS: int = 7  # days
    
    # -------------------- AI Pipeline Configuration --------------------
    # Expected frame rate from AI pipeline
    EXPECTED_FPS: int = 10

    # Optional: used only when running the Roboflow-based detector modes.
    # Keeping this here prevents startup failure if ROBOFLOW_API_KEY exists in .env.
    ROBOFLOW_API_KEY: Optional[str] = None
    
    # -------------------- System Mode Configuration --------------------
    # Mode: "playback" (uploaded videos) or "live" (real-time camera feeds)
    SYSTEM_MODE: str = "playback"

    # -------------------- Default beach / coastal context (Open-Meteo) --------------------
    # Used by /api/coastal/conditions when lat/lon not passed. Bondi Beach, NSW.
    BEACH_DEFAULT_LAT: float = -33.890842
    BEACH_DEFAULT_LON: float = 151.274291
    BEACH_DEFAULT_LABEL: str = "Bondi Beach, NSW"
    
    # -------------------- Server Configuration --------------------
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # Where the AI subprocess POSTs FrameResult ingest (same machine: defaults to this server’s PORT).
    # Override when the API is behind a proxy or reachable only at a public URL.
    BACKEND_URL: Optional[str] = None

    # Video upload cap (bytes). Enforced in /api/video/upload while streaming the body.
    MAX_UPLOAD_VIDEO_BYTES: int = 50 * 1024 * 1024  # 50 MB default
    
    class Config:
        """Pydantic configuration"""
        env_file = ".env"  # Load from .env file if it exists
        case_sensitive = False  # Environment variables are case-insensitive
        extra = "ignore"  # Ignore unrelated env vars instead of failing startup


# Global settings instance
# Import this in other modules: from app.config import settings
settings = Settings()


