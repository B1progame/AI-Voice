import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from backend.core.config import settings
from backend.core.logging_setup import setup_logging, get_logger
from backend.core.csrf import csrf_middleware
from backend.db.init_db import init_db, ensure_admin_user, ensure_admin_settings
from backend.routers.auth import router as auth_router
from backend.routers.me import router as me_router
from backend.routers.admin import router as admin_router
from backend.routers.conversations import router as conversations_router
from backend.routers.settings import router as settings_router

LOG = get_logger(__name__)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"
INDEX_HTML = FRONTEND_DIR / "index.html"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Log request start/end + status
        try:
            response: Response = await call_next(request)
            LOG.info('%s %s -> %s', request.method, request.url.path, response.status_code)
            return response
        except Exception:
            LOG.exception("Unhandled error while processing request: %s %s", request.method, request.url.path)
            raise


def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(
        title="AI Assistant MVP (Stage 1)",
        version="1.0.0",
    )

    # Ensure folders exist
    Path(settings.LOG_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.DB_DIR).mkdir(parents=True, exist_ok=True)

    # Middleware: request logging + CSRF (for cookie-based JWT)
    app.add_middleware(RequestLoggingMiddleware)
    app.middleware("http")(csrf_middleware)

    # Routers
    app.include_router(auth_router, prefix="/api")
    app.include_router(me_router, prefix="/api")
    app.include_router(admin_router, prefix="/api")
    app.include_router(settings_router, prefix="/api")
    app.include_router(conversations_router, prefix="/api")

    # Static
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.on_event("startup")
    def _startup():
        init_db()
        ensure_admin_settings()
        ensure_admin_user()
        LOG.info("Startup complete. DB=%s", settings.SQLALCHEMY_DATABASE_URL)

    # SPA routes: serve index.html for known frontend routes and any non-/api path (so refresh works)
    @app.get("/login")
    def spa_login():
        return FileResponse(str(INDEX_HTML))

    @app.get("/register")
    def spa_register():
        return FileResponse(str(INDEX_HTML))

    @app.get("/admin")
    def spa_admin():
        return FileResponse(str(INDEX_HTML))

    @app.get("/")
    def spa_root():
        return FileResponse(str(INDEX_HTML))

    # Catch-all for client-side routing (exclude /api and /static)
    @app.get("/{path:path}")
    def spa_catch_all(path: str):
        if path.startswith("api") or path.startswith("static"):
            return Response(status_code=404)
        return FileResponse(str(INDEX_HTML))

    return app


app = create_app()

if __name__ == "__main__":
    # Optional: direct python run (but recommended: uvicorn)
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=False,
        log_level="info",
    )