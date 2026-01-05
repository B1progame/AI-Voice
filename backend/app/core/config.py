from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    """
    Zentraler Settings-Container (Pydantic v2).
    Wichtig: Andere Module greifen auf diese Attribute zu:
      - log_path
      - database_url
      - ollama_url
      - jwt_* + cookie_*
      - admin_email/admin_password
      - system_prompt/ollama_model
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

    # Logging
    log_level: str = "INFO"
    log_path: str = "logs/app.log"

    # DB
    # db_path ist "menschlich" fürs Banner; wirklich genutzt wird database_url (SQLAlchemy)
    db_path: str = "backend/data/app.db"
    database_url: str | None = None

    @field_validator("database_url", mode="before")
    @classmethod
    def _default_database_url(cls, v, info):
        if v and str(v).strip():
            return str(v).strip()
        db_path = (info.data.get("db_path") or "backend/data/app.db").replace("\\", "/")
        # sqlite URL: sqlite:///relative/path.db
        return f"sqlite:///{db_path}"

    # Auth / Cookies / CSRF
    jwt_secret: str = "dev-change-me"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 Tage
    session_cookie_name: str = "session"
    csrf_cookie_name: str = "csrf_token"

    cookie_secure: bool = False
    cookie_samesite: str = "lax"  # "lax" oder "strict" oder "none"

    # Bootstrap Admin
    admin_email: str = "admin@example.local"
    admin_password: str = "admin"

    # Registrierung
    allow_registration: bool = True
    require_admin_approval: bool = False

    # Ollama
    ollama_host: str = "127.0.0.1"
    ollama_port: int = 11434
    ollama_url: str | None = None
    ollama_model: str = "llama3.1"
    system_prompt: str = "You are a helpful assistant."

    @field_validator("ollama_url", mode="before")
    @classmethod
    def _default_ollama_url(cls, v, info):
        if v and str(v).strip():
            return str(v).strip()
        host = info.data.get("ollama_host") or "127.0.0.1"
        port = info.data.get("ollama_port") or 11434
        return f"http://{host}:{port}"


settings = Settings()