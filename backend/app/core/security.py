from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from fastapi import HTTPException, Request, Response
from passlib.context import CryptContext

from backend.app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_jwt(payload: Dict[str, Any], expires_minutes: Optional[int] = None) -> str:
    """
    Signiert ein JWT. Erwartet i.d.R. {"sub": "<user_id>"}.
    """
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=expires_minutes or settings.jwt_expire_minutes)

    data = dict(payload)
    data["iat"] = int(now.timestamp())
    data["exp"] = int(exp.timestamp())

    return jwt.encode(data, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid session")


def _new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_auth_cookies(response: Response, token: str) -> str:
    """
    Setzt Session + CSRF Cookie.
    Frontend sendet CSRF im Header X-CSRF-Token (siehe api.js).
    """
    csrf = _new_csrf_token()

    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
        max_age=settings.jwt_expire_minutes * 60,
    )

    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
        max_age=settings.jwt_expire_minutes * 60,
    )

    return csrf


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key=settings.session_cookie_name, path="/")
    response.delete_cookie(key=settings.csrf_cookie_name, path="/")


def get_session_cookie(request: Request) -> Optional[str]:
    return request.cookies.get(settings.session_cookie_name)


def require_csrf(request: Request) -> None:
    """
    Schutz für state-changing requests (POST/PATCH/DELETE).
    Erwartung:
      - Cookie csrf_token
      - Header X-CSRF-Token identisch
    """
    if request.method.upper() in {"GET", "HEAD", "OPTIONS"}:
        return

    cookie_token = request.cookies.get(settings.csrf_cookie_name)
    header_token = request.headers.get("X-CSRF-Token")

    if not cookie_token or not header_token or cookie_token != header_token:
        raise HTTPException(status_code=403, detail="CSRF check failed")