from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000

    # Paths
    PROJECT_ROOT: str = str(Path(__file__).resolve().parent.parent.parent)
    DB_DIR: str = str(Path(PROJECT_ROOT) / "backend" / "data")
    LOG_DIR: str = str(Path(PROJECT_ROOT) / "logs")

    DB_FILENAME: str = "app.db"

    # Security
    JWT_SECRET: str = "CHANGE_ME"
    JWT_ALG: str = "HS256"
    JWT_EXPIRES_MINUTES: int = 60 * 24 * 7  # 7 days

    COOKIE_NAME: str = "access_token"
    COOKIE_SECURE: bool = True  # behind HTTPS proxy; in dev you can set false in .env
    COOKIE_SAMESITE: str = "lax"  # lax recommended for SPA behind same-origin
    COOKIE_DOMAIN: str | None = None  # usually None
    CSRF_COOKIE_NAME: str = "csrf_token"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"

    # Admin bootstrap
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "B1pro"
    ADMIN_FORCE_RESET: bool = False  # optional: reset admin password on startup if True

    # Ollama
    OLLAMA_URL: str = "http://localhost:11435"
    OLLAMA_MODEL: str = "llama3.1:8b"

    # LLM behavior
    LLM_MAX_CONTEXT_MESSAGES: int = 30

    # Optional: Web Search (SearXNG)
    # If not set, web_search/recipe_search tools must return a clear error (no fallback scraping).
    SEARXNG_URL: str | None = None

    # Tool timeouts (seconds)
    WEATHER_TIMEOUT_SECONDS: float = 12.0
    SEARCH_TIMEOUT_SECONDS: float = 12.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        db_path = Path(self.DB_DIR) / self.DB_FILENAME
        return f"sqlite:///{db_path.as_posix()}"


settings = Settings()