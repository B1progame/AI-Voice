from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.security import decode_access_token, get_token_from_request
from backend.app.db.session import SessionLocal
from backend.app.models.user import User
from backend.app.schemas.user import UserMeOut

router = APIRouter(tags=["me"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(request: Request, db: Session) -> User:
    token = get_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_access_token(token)
    user_id = int(payload.get("sub"))
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")
    return user


@router.get("/api/me", response_model=UserMeOut)
def me(request: Request, db: Session = Depends(get_db)) -> UserMeOut:
    user = get_current_user(request, db)
    return UserMeOut(id=user.id, email=user.email, role=user.role.value, status=user.status.value)


# Export dependency for other routers
def current_user_dep(request: Request, db: Session = Depends(get_db)) -> User:
    return get_current_user(request, db)