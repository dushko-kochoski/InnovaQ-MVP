"""Application settings loaded from .env via pydantic-settings."""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = parent of the backend/ package, so .env resolves the same
# way no matter which directory uvicorn/pytest is launched from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "InnovaQ"
    DATABASE_URL: str = f"sqlite:///{PROJECT_ROOT / 'innovaq.db'}"
    SECRET_KEY: str = "change-me-in-dotenv"
    FRONTEND_URL: str = "http://localhost:3000"
    DEBUG: bool = False

    # JWT
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h
    AUTH_COOKIE_NAME: str = "innovaq_access_token"

    # Workflow engine
    HTTP_ACTION_TIMEOUT_SECONDS: float = 15.0

    @field_validator("DATABASE_URL")
    @classmethod
    def _normalize_postgres_scheme(cls, value: str) -> str:
        # Railway/Heroku hand out postgres:// URLs; SQLAlchemy 2.x only
        # accepts postgresql://
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql://", 1)
        return value

    @field_validator("FRONTEND_URL")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        # CORS origin matching is exact — a trailing slash breaks it
        return value.rstrip("/")

    # Valid niches (single source of truth for models/schemas/routes)
    NICHES: tuple[str, ...] = (
        "accounting",
        "trade",
        "real_estate",
        "logistics",
        "healthcare",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
