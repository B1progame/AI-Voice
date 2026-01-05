from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class ConversationOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationCreateIn(BaseModel):
    title: str = Field(default="New chat", min_length=1, max_length=200)


class ConversationPatchIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)