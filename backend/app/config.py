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

import json
from typing import Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# The only list-shaped setting. It is stored as a string on purpose:
# pydantic-settings 2.1 JSON-decodes List fields before validators run, so a
# plain URL in ALLOWED_ORIGINS crashed Render at startup.
DEFAULT_ALLOWED_ORIGINS = [
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
    "https://beach-assistant-preview.vercel.app",
]


def parse_allowed_origins(value):
    """Accept one URL, a comma-separated list, a JSON list, or a Python list.

    pydantic-settings 2.1 raises SettingsError on a non-JSON env value when the
    field type is ``list``. Callers that build Settings keep the env value as
    text and parse it here.
    """
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "ALLOWED_ORIGINS must be one URL, a comma-separated list, "
                "or a JSON list of URLs"
            ) from exc
        if isinstance(parsed, str):
            parsed = [parsed]
        if not isinstance(parsed, list):
            raise ValueError("ALLOWED_ORIGINS JSON value must be a list of URLs")
        return [str(item).strip() for item in parsed if str(item).strip()]
    return [part.strip() for part in text.split(",") if part.strip()]


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
    
    # Raw env text. A List annotation makes pydantic-settings 2.1 require JSON.
    origins_from_env: str = Field(
        default="",
        validation_alias=AliasChoices("ALLOWED_ORIGINS"),
    )

    @property
    def ALLOWED_ORIGINS(self) -> list[str]:
        """CORS origins. Empty env keeps the local and Vercel defaults."""
        if not self.origins_from_env.strip():
            return list(DEFAULT_ALLOWED_ORIGINS)
        return parse_allowed_origins(self.origins_from_env)

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

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


# Global settings instance
# Import this in other modules: from app.config import settings
settings = Settings()


