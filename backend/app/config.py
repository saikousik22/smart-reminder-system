"""
Application configuration loaded from environment variables.
"""

import logging
from pydantic_settings import BaseSettings
from pydantic import model_validator
from functools import lru_cache
from typing import List
from sqlalchemy.engine import URL as SqlAlchemyURL

_logger = logging.getLogger(__name__)

_DEFAULT_JWT_SECRET = "change-this-secret-key-in-production"


class Settings(BaseSettings):
    # App
    APP_NAME: str = "SmartReminderSystem"
    DEBUG: bool = False

    # Database — individual fields so special characters need no URL-encoding
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "smart_reminder"
    DB_SSLMODE: str = "prefer"

    @property
    def db_url(self) -> SqlAlchemyURL:
        return SqlAlchemyURL.create(
            drivername="postgresql+psycopg2",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
            query={"sslmode": self.DB_SSLMODE},
        )

    # JWT
    JWT_SECRET_KEY: str = _DEFAULT_JWT_SECRET
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # Redis — individual fields so special characters in password need no URL-encoding
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_SSL: bool = False

    @property
    def redis_url(self) -> str:
        scheme = "rediss" if self.REDIS_SSL else "redis"
        if self.REDIS_PASSWORD:
            return f"{scheme}://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"{scheme}://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # Public URL (ngrok in dev, real URL in prod)
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    # Allowed CORS origins — override via env var as JSON array in production
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]

    # Azure Blob Storage
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_CONTAINER_NAME: str = "audio-files"

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
