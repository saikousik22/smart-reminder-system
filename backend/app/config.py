"""
Application configuration loaded from environment variables.
"""

import logging
from pydantic_settings import BaseSettings
from pydantic import model_validator
from functools import lru_cache
from typing import List

_logger = logging.getLogger(__name__)

_DEFAULT_JWT_SECRET = "change-this-secret-key-in-production"


class Settings(BaseSettings):
    # App
    APP_NAME: str = "SmartReminderSystem"
    # Default False — SQL query logging and other debug output are off unless explicitly enabled
    DEBUG: bool = False

    # Database — set DATABASE_URL in .env:
    # postgresql://user:password@host:5432/dbname
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/smart_reminder"

    # JWT
    JWT_SECRET_KEY: str = _DEFAULT_JWT_SECRET
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # Redis (Celery broker + backend)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Public URL (ngrok in dev, real URL in prod)
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    # Allowed CORS origins — override via env var as JSON array in production
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]

    # Set True in production (requires HTTPS)
    COOKIE_SECURE: bool = False

    @model_validator(mode="after")
    def check_secrets(self) -> "Settings":
        if self.JWT_SECRET_KEY == _DEFAULT_JWT_SECRET:
            if not self.DEBUG:
                raise ValueError(
                    "JWT_SECRET_KEY must be changed from the default insecure value before running in production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
                )
            _logger.warning(
                "JWT_SECRET_KEY is set to the default insecure value. "
                "Set a strong secret in .env before deploying to production."
            )
        return self

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
