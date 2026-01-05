from __future__ import annotations

from pydantic import BaseModel


class UserMeOut(BaseModel):
    id: int
    email: str
    role: str
    status: str