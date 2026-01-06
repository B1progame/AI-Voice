from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from backend.db.settings_crud import get_admin_settings
from backend.services.tools.context import ToolContext


_WEEKDAYS_DE = {
    "Monday": "Montag",
    "Tuesday": "Dienstag",
    "Wednesday": "Mittwoch",
    "Thursday": "Donnerstag",
    "Friday": "Freitag",
    "Saturday": "Samstag",
    "Sunday": "Sonntag",
}


def _weekday_localized(weekday_en: str, locale: str) -> str:
    loc = (locale or "").lower()
    if loc.startswith("de"):
        return _WEEKDAYS_DE.get(weekday_en, weekday_en)
    return weekday_en


def _format_local_datetime(dt: datetime, locale: str) -> str:
    loc = (locale or "").lower()
    if loc.startswith("de"):
        return dt.strftime("%d.%m.%Y %H:%M")
    return dt.strftime("%Y-%m-%d %H:%M")


def run(args: dict, ctx: ToolContext) -> dict:
    """Return current local datetime based on admin settings."""
    row = get_admin_settings(ctx.db)

    tz_name = row.timezone or "Europe/Berlin"
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")
        tz_name = "UTC"

    now = datetime.now(tz)
    weekday_en = now.strftime("%A")
    weekday = _weekday_localized(weekday_en, row.locale)

    return {
        "iso_datetime": now.isoformat(),
        "local_datetime": _format_local_datetime(now, row.locale),
        "weekday": weekday,
        "date": now.date().isoformat(),
        "time": now.strftime("%H:%M:%S"),
        "timezone": tz_name,
        "locale": row.locale,
    }