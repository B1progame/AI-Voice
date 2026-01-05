# backend/app/db/base.py
from __future__ import annotations

# SQLAlchemy 2.x preferred
try:
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):
        pass

except Exception:
    # Fallback for older SQLAlchemy (1.4 style)
    from sqlalchemy.ext.declarative import declarative_base  # type: ignore
    Base = declarative_base()