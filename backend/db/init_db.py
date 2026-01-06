from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.logging_setup import get_logger
from backend.core.security import hash_password
from backend.db.database import engine, SessionLocal, Base
from backend.db import models  # noqa: F401  (ensures models are imported for metadata)
from backend.db.settings_crud import ensure_admin_settings_row

LOG = get_logger(__name__)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def ensure_admin_settings() -> None:
    db: Session = SessionLocal()
    try:
        ensure_admin_settings_row(db)
        LOG.info("Admin settings ensured")
    finally:
        db.close()


def ensure_admin_user() -> None:
    db: Session = SessionLocal()
    try:
        admin = db.query(models.User).filter(models.User.email == settings.ADMIN_EMAIL).first()
        if admin is None:
            admin = models.User(
                email=settings.ADMIN_EMAIL,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                role="admin",
                status="approved",
            )
            db.add(admin)
            db.commit()
            LOG.info("Admin user created: %s", settings.ADMIN_EMAIL)
        else:
            # Ensure admin has correct role/status
            changed = False
            if admin.role != "admin":
                admin.role = "admin"
                changed = True
            if admin.status != "approved":
                admin.status = "approved"
                changed = True

            if settings.ADMIN_FORCE_RESET:
                admin.password_hash = hash_password(settings.ADMIN_PASSWORD)
                changed = True

            if changed:
                db.commit()
                LOG.info("Admin user ensured/updated: %s (force_reset=%s)", settings.ADMIN_EMAIL, settings.ADMIN_FORCE_RESET)
    finally:
        db.close()