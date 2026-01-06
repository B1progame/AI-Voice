from fastapi import APIRouter, Depends, Response, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.security import hash_password, verify_password, create_access_token, new_csrf_token
from backend.db.database import get_db
from backend.db.models import User
from backend.schemas.auth import RegisterIn, LoginIn

router = APIRouter(tags=["auth"])


def _set_auth_cookies(resp: Response, token: str, csrf: str) -> None:
    resp.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/",
        max_age=settings.JWT_EXPIRES_MINUTES * 60,
    )
    resp.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/",
        max_age=settings.JWT_EXPIRES_MINUTES * 60,
    )


def _clear_auth_cookies(resp: Response) -> None:
    resp.delete_cookie(key=settings.COOKIE_NAME, path="/", domain=settings.COOKIE_DOMAIN)
    resp.delete_cookie(key=settings.CSRF_COOKIE_NAME, path="/", domain=settings.COOKIE_DOMAIN)


@router.post("/auth/register")
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    exists = db.query(User).filter(User.email == email).first()
    if exists:
        return JSONResponse(status_code=400, content={"detail": "Email already registered"})

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        role="user",
        status="pending",
    )
    db.add(user)
    db.commit()
    return {"ok": True, "status": "pending", "message": "Registered. Awaiting admin approval."}


@router.post("/auth/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return JSONResponse(status_code=401, content={"detail": "Invalid credentials"})

    if user.status != "approved":
        return JSONResponse(status_code=403, content={"detail": f"User not approved (status={user.status})"})

    if not verify_password(payload.password, user.password_hash):
        return JSONResponse(status_code=401, content={"detail": "Invalid credentials"})

    token = create_access_token(subject=str(user.id), role=user.role)
    csrf = new_csrf_token()

    resp = JSONResponse(
        status_code=200,
        content={"ok": True, "message": "Logged in"},
    )
    _set_auth_cookies(resp, token, csrf)
    return resp


@router.post("/auth/logout")
def logout(request: Request):
    resp = JSONResponse(status_code=200, content={"ok": True, "message": "Logged out"})
    _clear_auth_cookies(resp)
    return resp