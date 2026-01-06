from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class AdminSettingsOut(BaseModel):
    timezone: str
    locale: str
    country: str
    default_location_name: str | None
    default_lat: float | None
    default_lon: float | None
    units: str


class AdminSettingsUpdateIn(BaseModel):
    timezone: str | None = Field(default=None)
    locale: str | None = Field(default=None)
    country: str | None = Field(default=None)
    default_location_name: str | None = Field(default=None)
    default_lat: float | None = Field(default=None)
    default_lon: float | None = Field(default=None)
    units: str | None = Field(default=None)

    @field_validator("units")
    @classmethod
    def _units(cls, v: str | None):
        if v is None:
            return v
        if v not in ("metric", "imperial"):
            raise ValueError("units must be metric or imperial")
        return v


class PublicSettingsOut(AdminSettingsOut):
    pass