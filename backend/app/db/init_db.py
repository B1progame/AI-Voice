from __future__ import annotations

import logging
from sqlalchemy import select

from backend.app.core.security import hash_password
from backend.app.core.config import settings
from backend.app.db.session import Base, engine, SessionLocal
from backend.app.models.user import User, UserRole, UserStatus

logger = logging.getLogger(__name__)


def init_db_and_bootstrap_admin() -> None:
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        existing_admin = db.execute(
            select(User).where(User.email == settings.admin_email)
        ).scalar_one_or_none()

        if existing_admin:
            # Ensure admin role/status at least
            changed = False
            if existing_admin.role != UserRole.admin:
                existing_admin.role = UserRole.admin
                changed = True
            if existing_admin.status != UserStatus.approved:
                existing_admin.status = UserStatus.approved
                changed = True
            if changed:
                db.add(existing_admin)
                db.commit()
                logger.info("Updated existing admin to role=admin and status=approved")
            else:
                logger.info("Admin already exists: %s", settings.admin_email)
            return

        admin = User(
            email=settings.admin_email,
            password_hash=hash_password(settings.admin_password),
            role=UserRole.admin,
            status=UserStatus.approved,
        )
        db.add(admin)
        db.commit()
        logger.info("Created bootstrap admin: %s", settings.admin_email)