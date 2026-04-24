"""
Coastal conditions (live context for lifeguard dashboard)
=========================================================
Proxies Open-Meteo Marine + Weather APIs (free tier, no API key).
https://open-meteo.com/ — attribution in responses for UI.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/coastal", tags=["coastal"])

MARINE_BASE = "https://marine-api.open-meteo.com/v1/marine"
WEATHER_BASE = "https://api.open-meteo.com/v1/forecast"

MARINE_HOURLY = (
    "wave_height,wave_direction,wave_period,"
    "swell_wave_height,swell_wave_direction,swell_wave_period,"
    "wind_wave_height,sea_surface_temperature"
)


def _pick_hourly_index(times: list[str]) -> int:
    """Pick index closest to current UTC hour."""
    if not times:
        return 0
    now = datetime.now(timezone.utc)
    try:
        best_i = 0
        best_delta = float("inf")
        for i, t in enumerate(times):
            # ISO8601 from API
            ts = datetime.fromisoformat(t.replace("Z", "+00:00"))
            delta = abs((ts - now).total_seconds())
            if delta < best_delta:
                best_delta = delta
                best_i = i
        return min(best_i, len(times) - 1)
    except Exception:
        return 0


def _safe_float(series: Optional[list], idx: int) -> Optional[float]:
    if not series or idx >= len(series):
        return None
    v = series[idx]
    return float(v) if v is not None else None


@router.get("/conditions")
async def get_coastal_conditions(
    latitude: Optional[float] = Query(None, ge=-90, le=90, description="Beach latitude"),
    longitude: Optional[float] = Query(None, ge=-180, le=180, description="Beach longitude"),
) -> dict[str, Any]:
    """
    Combined marine + surface weather for dashboard context (waves, swell, SST, wind).
    No API key required. Data is indicative; not for navigation / emergency decisions.
    """
    lat = latitude if latitude is not None else settings.BEACH_DEFAULT_LAT
    lon = longitude if longitude is not None else settings.BEACH_DEFAULT_LON
    label = settings.BEACH_DEFAULT_LABEL

    timeout = httpx.Timeout(12.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        marine_params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": MARINE_HOURLY,
            "forecast_days": 2,
        }
        weather_params = {
            "latitude": lat,
            "longitude": lon,
            "current": "wind_speed_10m,wind_direction_10m,weather_code,is_day",
            "wind_speed_unit": "kmh",
        }

        marine_data: dict[str, Any] = {}
        weather_data: dict[str, Any] = {}
        errors: list[str] = []

        try:
            r = await client.get(MARINE_BASE, params=marine_params)
            r.raise_for_status()
            marine_data = r.json()
        except Exception as e:
            logger.warning("Marine API failed: %s", e)
            errors.append(f"marine: {e!s}")

        try:
            r = await client.get(WEATHER_BASE, params=weather_params)
            r.raise_for_status()
            weather_data = r.json()
        except Exception as e:
            logger.warning("Weather API failed: %s", e)
            errors.append(f"weather: {e!s}")

    hourly = marine_data.get("hourly") or {}
    times = hourly.get("time") or []
    idx = _pick_hourly_index(times)

    marine_snapshot = {
        "time_utc": times[idx] if times else None,
        "wave_height_m": _safe_float(hourly.get("wave_height"), idx),
        "wave_direction_deg": _safe_float(hourly.get("wave_direction"), idx),
        "wave_period_s": _safe_float(hourly.get("wave_period"), idx),
        "swell_height_m": _safe_float(hourly.get("swell_wave_height"), idx),
        "swell_direction_deg": _safe_float(hourly.get("swell_wave_direction"), idx),
        "swell_period_s": _safe_float(hourly.get("swell_wave_period"), idx),
        "wind_wave_height_m": _safe_float(hourly.get("wind_wave_height"), idx),
        "sea_surface_temp_c": _safe_float(hourly.get("sea_surface_temperature"), idx),
    }

    current = weather_data.get("current") or {}
    weather_snapshot = {
        "wind_speed_kmh": current.get("wind_speed_10m"),
        "wind_direction_deg": current.get("wind_direction_10m"),
        "weather_code": current.get("weather_code"),
        "is_day": current.get("is_day"),
    }

    if not times and not current:
        raise HTTPException(
            status_code=502,
            detail="Could not fetch coastal data from Open-Meteo. " + "; ".join(errors),
        )

    return {
        "location": {
            "latitude": lat,
            "longitude": lon,
            "label": label,
        },
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "marine": marine_snapshot,
        "weather": weather_snapshot,
        "partial": bool(errors),
        "warnings": errors,
        "attribution": (
            "Weather & marine data by Open-Meteo (open-meteo.com) — "
            "non-commercial use; not a substitute for official marine warnings."
        ),
    }
