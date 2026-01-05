from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.security import (
    clear_auth_cookies,
    create_access_token,
    new_csrf_token,
    set_auth_cookies,
    verify_password,
)
from backend.app.db.session import get_db
from backend.app.models.user import User, UserRole, UserStatus
from backend.app.schemas.auth import RegisterIn, SimpleOut
from backend.app.schemas.user import UserMeOut
from backend.app.core.security import hash_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=SimpleOut)
def register(payload: RegisterIn, db: Session = Depends(get_db)) -> SimpleOut:
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.USER,
        status=UserStatus.PENDING,
    )
    db.add(user)
    db.commit()
    return SimpleOut(ok=True, message="registered")


@router.post("/login", response_model=UserMeOut)
async def login(request: Request, response: Response, db: Session = Depends(get_db)) -> UserMeOut:
    # Accept BOTH:
    # - application/x-www-form-urlencoded: username/password (frontend does this first)
    # - application/json: email/password
    content_type = (request.headers.get("content-type") or "").lower()

    email = None
    password = None

    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        email = (form.get("email") or form.get("username") or "").strip()
        password = (form.get("password") or "")
    else:
        try:
            body = await request.json()
        except Exception:
            body = {}
        email = str(body.get("email") or body.get("username") or "").strip()
        password = str(body.get("password") or "")

    if not email or not password:
        raise HTTPException(status_code=422, detail="email and password required")

    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Only approved users can log in (admins always can)
    if user.role != UserRole.ADMIN and user.status != UserStatus.APPROVED:
        raise HTTPException(status_code=403, detail="User not approved yet")

    token = create_access_token(subject=str(user.id), role=user.role.value)
    csrf = new_csrf_token()
    set_auth_cookies(response, token, csrf)

    return UserMeOut(id=user.id, email=user.email, role=user.role.value, status=user.status.value)


@router.post("/logout", response_model=SimpleOut)
def logout(response: Response) -> SimpleOut:
    clear_auth_cookies(response)
    return SimpleOut(ok=True, message="logged out")