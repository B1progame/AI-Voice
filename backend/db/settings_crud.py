from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from backend.db.models import AdminSettings

# Singleton defaults (exactly one row with id=1)
DEFAULTS: dict[str, Any] = {
    "timezone": "Europe/Berlin",
    "locale": "de-DE",
    "country": "DE",
    "default_location_name": None,
    "default_lat": None,
    "default_lon": None,
    "units": "metric",
}


def ensure_admin_settings_row(db: Session) -> AdminSettings:
    """Ensure the singleton AdminSettings row exists (id=1).

    Safe to call on every startup.
    """
    row = db.query(AdminSettings).filter(AdminSettings.id == 1).first()
    if row is None:
        row = AdminSettings(id=1, **DEFAULTS)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def get_admin_settings(db: Session) -> AdminSettings:
    row = db.query(AdminSettings).filter(AdminSettings.id == 1).first()
    if row is None:
        row = ensure_admin_settings_row(db)
    return row


def update_admin_settings(db: Session, data: dict[str, Any]) -> AdminSettings:
    row = get_admin_settings(db)

    # Only update known keys.
    for k in DEFAULTS.keys():
        if k in data:
            setattr(row, k, data[k])

    db.commit()
    db.refresh(row)
    return row


def to_public_dict(row: AdminSettings) -> dict[str, Any]:
    return {
        "timezone": row.timezone,
        "locale": row.locale,
        "country": row.country,
        "default_location_name": row.default_location_name,
        "default_lat": row.default_lat,
        "default_lon": row.default_lon,
        "units": row.units,
    }