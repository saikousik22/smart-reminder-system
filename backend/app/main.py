"""
FastAPI application entry point.
Configures CORS and mounts routers. Audio files are stored in Azure Blob Storage.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routers import auth_router, reminder_router, voice_router, template_router, translate_router, dashboard_router, contacts_router, groups_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME}...")
    yield
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
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# Include routers
app.include_router(auth_router.router)
app.include_router(reminder_router.router)
app.include_router(voice_router.router)
app.include_router(template_router.router)
app.include_router(translate_router.router)
app.include_router(dashboard_router.router)
app.include_router(contacts_router.router)
app.include_router(groups_router.router)


@app.get("/", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "message": "Smart Reminder System API is running!",
    }
