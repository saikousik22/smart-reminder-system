"""
Redis-backed rate limiter used as a FastAPI dependency.

Uses Redis INCR + EXPIRE for atomic, cross-process counting (works across
multiple uvicorn workers and App Service instances). Falls back to an
in-memory sliding-window counter when Redis is unreachable so auth endpoints
remain functional during a Redis outage.
"""

import logging
import time
import threading
from collections import defaultdict

import redis as redis_lib
from fastapi import HTTPException, Request

from app.config import get_settings

logger = logging.getLogger(__name__)

_WINDOW = 60  # 60-second window

# In-memory fallback — single-process only, used when Redis is down
_fallback: dict[str, list[float]] = defaultdict(list)
_fallback_lock = threading.Lock()


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _redis_check(key: str, max_requests: int) -> bool | None:
    """Increment the Redis counter and return True if under limit.

    Returns None when Redis is unavailable so the caller can fall back to
    in-memory counting.
    """
    settings = get_settings()
    try:
        r = redis_lib.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD or None,
            ssl=settings.REDIS_SSL,
            ssl_cert_reqs=None,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, _WINDOW)
        count, _ = pipe.execute()
        return count <= max_requests
    except Exception as exc:
        logger.debug("Rate limiter Redis unavailable, using in-memory fallback: %s", exc)
        return None


def _memory_check(key: str, max_requests: int) -> bool:
    now = time.time()
    cutoff = now - _WINDOW
    with _fallback_lock:
        _fallback[key] = [t for t in _fallback[key] if t > cutoff]
        if len(_fallback[key]) >= max_requests:
            return False
        _fallback[key].append(now)
        return True


def _check(request: Request, max_requests: int, label: str) -> None:
    ip = _get_client_ip(request)
    key = f"rl:{label}:{ip}"

    result = _redis_check(key, max_requests)
    if result is None:
        result = _memory_check(key, max_requests)

    if not result:
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")


def login_rate_limit(request: Request) -> None:
    _check(request, max_requests=5, label="login")


def signup_rate_limit(request: Request) -> None:
    _check(request, max_requests=3, label="signup")
