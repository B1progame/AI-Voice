from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from backend.core.config import settings
from backend.core.logging_setup import get_logger
from backend.db.settings_crud import get_admin_settings
from backend.services.tools.context import ToolContext
from backend.services.tools.errors import ToolError

LOG = get_logger(__name__)


def _open_meteo_units(row_units: str) -> dict[str, str]:
    # Open-Meteo accepts explicit units params.
    if row_units == "imperial":
        return {
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
        }
    return {
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
    }


def _geocode_open_meteo(name: str, *, language: str = "de") -> tuple[float, float, str]:
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": name,
        "count": 1,
        "language": language,
        "format": "json",
    }
    timeout = httpx.Timeout(connect=5.0, read=settings.WEATHER_TIMEOUT_SECONDS, write=10.0, pool=10.0)
    with httpx.Client(timeout=timeout) as client:
        r = client.get(url, params=params)
        r.raise_for_status()
        data = r.json()

    results = data.get("results") or []
    if not results:
        raise ToolError(f"Ort nicht gefunden: {name}")

    top = results[0]
    lat = top.get("latitude")
    lon = top.get("longitude")
    disp = top.get("name")
    country = top.get("country")
    admin1 = top.get("admin1")
    if lat is None or lon is None:
        raise ToolError(f"Geocoding fehlgeschlagen für: {name}")

    parts = [p for p in [disp, admin1, country] if p]
    return float(lat), float(lon), ", ".join(parts) if parts else name


def _forecast_open_meteo(lat: float, lon: float, *, timezone: str, units: str) -> dict[str, Any]:
    url = "https://api.open-meteo.com/v1/forecast"
    unit_params = _open_meteo_units(units)
    params: dict[str, Any] = {
        "latitude": lat,
        "longitude": lon,
        "timezone": timezone,
        "current": "temperature_2m,wind_speed_10m,precipitation",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
        "forecast_days": 4,
    }
    params.update(unit_params)

    timeout = httpx.Timeout(connect=5.0, read=settings.WEATHER_TIMEOUT_SECONDS, write=10.0, pool=10.0)
    with httpx.Client(timeout=timeout) as client:
        r = client.get(url, params=params)
        r.raise_for_status()
        return r.json()


def run(args: dict, ctx: ToolContext) -> dict:
    row = get_admin_settings(ctx.db)

    location = (args or {}).get("location")
    location = location.strip() if isinstance(location, str) else None

    tz = row.timezone or "Europe/Berlin"
    units = row.units or "metric"

    if location:
        lat, lon, resolved_name = _geocode_open_meteo(location, language=(row.locale or "de").split("-")[0] or "de")
    else:
        if row.default_lat is None or row.default_lon is None:
            raise ToolError(
                "Default location nicht gesetzt. Bitte im Admin-Panel unter Settings default_lat/default_lon setzen oder eine Location angeben."
            )
        lat = float(row.default_lat)
        lon = float(row.default_lon)
        resolved_name = row.default_location_name or "Default Location"

    t0 = datetime.utcnow()
    try:
        raw = _forecast_open_meteo(lat, lon, timezone=tz, units=units)
    except httpx.TimeoutException:
        raise ToolError("Weather request timeout")
    except Exception as e:
        LOG.exception("Weather request failed")
        raise ToolError("Weather request failed") from e
    finally:
        dt_ms = int((datetime.utcnow() - t0).total_seconds() * 1000)
        LOG.info("tool=get_weather lat=%s lon=%s duration_ms=%s", lat, lon, dt_ms)

    current = raw.get("current") or {}
    daily = raw.get("daily") or {}

    times = daily.get("time") or []
    tmax = daily.get("temperature_2m_max") or []
    tmin = daily.get("temperature_2m_min") or []
    psum = daily.get("precipitation_sum") or []
    wmax = daily.get("wind_speed_10m_max") or []

    days = []
    for i in range(min(3, len(times))):
        days.append(
            {
                "date": times[i],
                "temp_max": tmax[i] if i < len(tmax) else None,
                "temp_min": tmin[i] if i < len(tmin) else None,
                "precipitation_sum": psum[i] if i < len(psum) else None,
                "wind_max": wmax[i] if i < len(wmax) else None,
            }
        )

    return {
        "location": {
            "name": resolved_name,
            "latitude": lat,
            "longitude": lon,
        },
        "timezone": tz,
        "units": units,
        "current": {
            "time": current.get("time"),
            "temperature": current.get("temperature_2m"),
            "wind_speed": current.get("wind_speed_10m"),
            "precipitation": current.get("precipitation"),
        },
        "forecast": days,
    }