"""
Application configuration loaded from environment variables.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "SmartReminderSystem"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./reminders.db"

    # JWT
    JWT_SECRET_KEY: str = "change-this-secret-key-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # Public URL (ngrok in dev, real URL in prod)
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    # Allowed CORS origins — override via env var as JSON array in production
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]

    # Set True in production (requires HTTPS)
    COOKIE_SECURE: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
