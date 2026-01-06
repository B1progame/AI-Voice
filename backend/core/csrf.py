from fastapi import Request
from starlette.responses import JSONResponse, Response

from backend.core.config import settings


EXEMPT_PATHS_PREFIX = (
    "/api/auth/login",
    "/api/auth/register",
)

# We enforce CSRF only when:
# - request is state-changing (POST/PATCH/DELETE)
# - user is authenticated via cookie (access_token present)
# - path is under /api
# - path is NOT exempt (login/register)
#
# Client must send:
# - cookie csrf_token
# - header X-CSRF-Token with same value
#
# This is a classic "double submit cookie" pattern for SPA.
async def csrf_middleware(request: Request, call_next):
    method = request.method.upper()
    path = request.url.path

    if not path.startswith("/api"):
        return await call_next(request)

    if method in ("GET", "HEAD", "OPTIONS"):
        return await call_next(request)

    if any(path.startswith(p) for p in EXEMPT_PATHS_PREFIX):
        return await call_next(request)

    access_cookie = request.cookies.get(settings.COOKIE_NAME)
    if not access_cookie:
        # Not logged in -> CSRF not required (request will likely fail auth anyway)
        return await call_next(request)

    csrf_cookie = request.cookies.get(settings.CSRF_COOKIE_NAME)
    csrf_header = request.headers.get(settings.CSRF_HEADER_NAME)

    if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
        return JSONResponse(
            status_code=403,
            content={"detail": "CSRF validation failed"},
        )

    resp: Response = await call_next(request)
    return resp