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
from typing import List


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
    # Allow frontend to connect from these origins
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",      # React dev server
        "http://localhost:5173",      # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
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
    
    # -------------------- Server Configuration --------------------
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    class Config:
        """Pydantic configuration"""
        env_file = ".env"  # Load from .env file if it exists
        case_sensitive = False  # Environment variables are case-insensitive


# Global settings instance
# Import this in other modules: from app.config import settings
settings = Settings()

