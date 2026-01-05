from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.security import require_csrf_for_unsafe_methods
from backend.app.db.session import SessionLocal
from backend.app.models.user import User, UserStatus, UserRole
from backend.app.routers.me import current_user_dep

router = APIRouter(prefix="/api/admin", tags=["admin"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_admin(user: User) -> None:
    if user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin only")


@router.get("/users")
def list_users(
    status: str = "pending",
    user: User = Depends(current_user_dep),
    db: Session = Depends(get_db),
):
    require_admin(user)

    try:
        status_enum = UserStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")

    users = (
        db.execute(select(User).where(User.status == status_enum).order_by(User.created_at.asc()))
        .scalars()
        .all()
    )
    return {
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "status": u.status.value,
                "role": u.role.value,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ]
    }


@router.post("/users/{user_id}/approve")
def approve_user(
    user_id: int,
    request: Request,
    user: User = Depends(current_user_dep),
    db: Session = Depends(get_db),
):
    require_admin(user)
    require_csrf_for_unsafe_methods(request)

    target = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target.status = UserStatus.approved
    db.add(target)
    db.commit()
    return {"ok": True}


@router.post("/users/{user_id}/deny")
def deny_user(
    user_id: int,
    request: Request,
    user: User = Depends(current_user_dep),
    db: Session = Depends(get_db),
):
    require_admin(user)
    require_csrf_for_unsafe_methods(request)

    target = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if target.role == UserRole.admin:
        raise HTTPException(status_code=400, detail="Cannot deny admin user")

    target.status = UserStatus.denied
    db.add(target)
    db.commit()
    return {"ok": True}