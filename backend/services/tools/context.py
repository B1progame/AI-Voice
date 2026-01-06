from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.db.models import User


@dataclass(frozen=True)
class ToolContext:
    db: Session
    user: User