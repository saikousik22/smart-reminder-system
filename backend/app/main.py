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
    url = settings.redis_url
    masked = url.split("@")[-1] if "@" in url else url
    logger.info(f"Starting {settings.APP_NAME}... Redis target: {masked}")
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
    return {"status": "healthy", "app": settings.APP_NAME}


@app.get("/health/redis", tags=["Health"])
def redis_health():
    import redis as redis_lib
    pwd = settings.REDIS_PASSWORD
    try:
        r = redis_lib.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=pwd if pwd else None,
            ssl=settings.REDIS_SSL,
            ssl_cert_reqs=None,
            socket_connect_timeout=5,
        )
        r.ping()
        return {
            "status": "ok",
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT,
            "ssl": settings.REDIS_SSL,
            "pwd_len": len(pwd),
            "pwd_prefix": pwd[:4] if pwd else "",
        }
    except Exception as exc:
        return {
            "status": "error",
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT,
            "ssl": settings.REDIS_SSL,
            "pwd_len": len(pwd),
            "pwd_prefix": pwd[:4] if pwd else "",
            "detail": str(exc),
        }


@app.get("/health/celery", tags=["Health"])
def celery_health():
    import redis as redis_lib
    from app.celery_app import celery_app
    pwd = settings.REDIS_PASSWORD

    # Check Redis for any Celery worker heartbeat keys
    try:
        r = redis_lib.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=pwd if pwd else None,
            ssl=settings.REDIS_SSL,
            ssl_cert_reqs=None,
            socket_connect_timeout=5,
        )
        celery_keys = [k.decode() for k in r.keys("*celery*") or []]
        kombu_keys = [k.decode() for k in r.keys("*kombu*") or []]
    except Exception as exc:
        return {"status": "error", "detail": f"redis error: {exc}"}

    # Ping workers via control channel
    try:
        ping = celery_app.control.inspect(timeout=5).ping()
        workers = list(ping.keys()) if ping else []
    except Exception as exc:
        workers = []
        ping_error = str(exc)
    else:
        ping_error = None

    return {
        "status": "ok" if workers else "error",
        "workers": workers,
        "celery_redis_keys": celery_keys,
        "kombu_redis_keys": kombu_keys,
        "ping_error": ping_error,
    }
