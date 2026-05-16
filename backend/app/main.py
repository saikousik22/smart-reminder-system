"""
FastAPI application entry point.
Configures CORS, audit middleware, and mounts routers.
Audio files are stored in Azure Blob Storage.
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.routers import (
    auth_router, reminder_router, voice_router, template_router,
    translate_router, dashboard_router, contacts_router, groups_router,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


# ── Audit middleware ───────────────────────────────────────────────────────────

def _extract_user_id(request: Request) -> str | None:
    """Best-effort extraction of user_id from JWT for audit logging."""
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        token = auth[len("Bearer "):].strip() if auth.startswith("Bearer ") else None
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False},
        )
        return str(payload.get("sub", ""))
    except (JWTError, Exception):
        return None


class AuditMiddleware(BaseHTTPMiddleware):
    """Log every API request with user identity, status code, and latency."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        user_id = _extract_user_id(request)
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        # Skip noisy health-check paths
        if not request.url.path.startswith("/health"):
            logger.info(
                "AUDIT | %s %s | user=%s | status=%d | %.0fms",
                request.method,
                request.url.path,
                user_id or "anon",
                response.status_code,
                duration_ms,
            )
        return response


# ── App lifespan ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    url = settings.redis_url
    masked = url.split("@")[-1] if "@" in url else url
    logger.info(f"Starting {settings.APP_NAME}... Redis target: {masked}")
    yield
    logger.info(f"{settings.APP_NAME} shut down.")


# ── FastAPI app ────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description="A smart reminder system that calls you with your recorded voice message.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(AuditMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

app.include_router(auth_router.router)
app.include_router(reminder_router.router)
app.include_router(voice_router.router)
app.include_router(template_router.router)
app.include_router(translate_router.router)
app.include_router(dashboard_router.router)
app.include_router(contacts_router.router)
app.include_router(groups_router.router)


# ── Health endpoints ───────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def health_check():
    return {"status": "healthy", "app": settings.APP_NAME}


@app.get("/health/redis", tags=["Health"])
def redis_health():
    import redis as redis_lib
    try:
        r = redis_lib.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD or None,
            ssl=settings.REDIS_SSL,
            ssl_cert_reqs=None,
            socket_connect_timeout=5,
        )
        r.ping()
        # SECURITY: never expose password prefix or length in responses
        return {
            "status": "ok",
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT,
            "ssl": settings.REDIS_SSL,
            "auth": bool(settings.REDIS_PASSWORD),
        }
    except Exception as exc:
        return {
            "status": "error",
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT,
            "ssl": settings.REDIS_SSL,
            "auth": bool(settings.REDIS_PASSWORD),
            "detail": str(exc),
        }


@app.get("/health/celery", tags=["Health"])
def celery_health():
    import redis as redis_lib
    from app.celery_app import celery_app
    try:
        r = redis_lib.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD or None,
            ssl=settings.REDIS_SSL,
            ssl_cert_reqs=None,
            socket_connect_timeout=5,
        )
        celery_keys = [k.decode() for k in r.keys("*celery*") or []]
        kombu_keys = [k.decode() for k in r.keys("*kombu*") or []]
    except Exception as exc:
        return {"status": "error", "detail": f"redis error: {exc}"}

    try:
        ping = celery_app.control.inspect(timeout=10).ping()
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
