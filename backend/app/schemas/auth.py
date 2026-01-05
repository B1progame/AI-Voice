# backend/app/schemas/auth.py
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


def _basic_email_ok(v: str) -> bool:
    # erlaubt auch admin@example.local oder admin@localhost
    if "@" not in v:
        return False
    left, right = v.split("@", 1)
    return bool(left.strip()) and bool(right.strip())


class RegisterIn(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=3, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip()
        if not _basic_email_ok(v):
            raise ValueError("Invalid email format (must contain '@').")
        return v


class LoginIn(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip()
        if not _basic_email_ok(v):
            raise ValueError("Invalid email format (must contain '@').")
        return v


class SimpleOut(BaseModel):
    ok: bool = True
    message: str = "ok"