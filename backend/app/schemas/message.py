from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime


class MessageCreateIn(BaseModel):
    content: str = Field(min_length=1, max_length=20000)