"""
FastAPI application entry point.
Configures CORS, mounts routers, serves audio files, and starts the scheduler.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from app.config import get_settings
from app.database import engine, Base
from app.scheduler import start_scheduler, stop_scheduler
from app.routers import auth_router, reminder_router, voice_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Uploads live at backend/uploads/, one level above this file's package dir
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _run_migrations():
    """Add columns introduced after initial schema creation (safe to re-run)."""
    new_columns = [
        ("retry_count", "INTEGER NOT NULL DEFAULT 0"),
        ("retry_gap_minutes", "INTEGER NOT NULL DEFAULT 10"),
        ("attempt_number", "INTEGER NOT NULL DEFAULT 1"),
        ("parent_reminder_id", "INTEGER"),
    ]
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(reminders)"))
        existing = {row[1] for row in result}
        for col_name, col_def in new_columns:
            if col_name not in existing:
                conn.execute(text(f"ALTER TABLE reminders ADD COLUMN {col_name} {col_def}"))
                conn.commit()
                logger.info(f"Migration: added column '{col_name}' to reminders table.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME}...")

    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")

    # Add new columns to existing tables (SQLite doesn't support IF NOT EXISTS for columns)
    _run_migrations()
    logger.info("Database migrations applied.")

    # Start the background scheduler
    start_scheduler()

    yield

    # Shutdown
    stop_scheduler()
    logger.info(f"{settings.APP_NAME} shut down.")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="A smart reminder system that calls you with your recorded voice message.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware — allow React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount audio files as static files (publicly accessible)
app.mount("/audio", StaticFiles(directory=UPLOAD_DIR), name="audio")

# Include routers
app.include_router(auth_router.router)
app.include_router(reminder_router.router)
app.include_router(voice_router.router)


@app.get("/", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "message": "Smart Reminder System API is running!",
    }
