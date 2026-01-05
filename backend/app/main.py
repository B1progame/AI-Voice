from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.core.logging import setup_logging
from backend.app.db.init_db import init_db_and_bootstrap_admin
from backend.app.middleware.request_logging import request_logging_middleware
from backend.app.routers.auth import router as auth_router
from backend.app.routers.me import router as me_router
from backend.app.routers.admin import router as admin_router
from backend.app.routers.conversations import router as conv_router

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
ASSETS_DIR = FRONTEND_DIR / "assets"


def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(title="AI Assistant Server (MVP)")

    # Middleware: request logging
    app.middleware("http")(request_logging_middleware)

    # Routers
    app.include_router(auth_router)
    app.include_router(me_router)
    app.include_router(admin_router)
    app.include_router(conv_router)

    # Serve frontend assets
    if not ASSETS_DIR.exists():
        logger.warning("Assets dir not found: %s", ASSETS_DIR)
    else:
        app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

    # SPA routes: serve index.html for /, /login, /register, /admin
    index_file = FRONTEND_DIR / "index.html"

    @app.get("/")
    def spa_root():
        return FileResponse(str(index_file))

    @app.get("/login")
    def spa_login():
        return FileResponse(str(index_file))

    @app.get("/register")
    def spa_register():
        return FileResponse(str(index_file))

    @app.get("/admin")
    def spa_admin():
        return FileResponse(str(index_file))

    @app.on_event("startup")
    def on_startup():
        logger.info("Starting up: init DB and bootstrap admin if needed")
        init_db_and_bootstrap_admin()

    return app


app = create_app()