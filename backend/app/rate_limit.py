"""
Simple in-memory rate limiter used as a FastAPI dependency.
Per-process only — not shared across multiple uvicorn workers or App Service instances.
For a multi-process production deployment, replace _check() with a Redis INCR+EXPIRE
implementation. The logic here still meaningfully limits single-IP abuse within one worker.
"""

import time
import threading
from collections import defaultdict
from fastapi import HTTPException, Request

_request_log: dict[str, list[float]] = defaultdict(list)
_lock = threading.Lock()
_WINDOW = 60.0  # seconds


def _get_client_ip(request: Request) -> str:
    # Azure App Service and most proxies set X-Forwarded-For.
    # Fall back to direct connection IP if the header is absent.
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check(request: Request, max_requests: int) -> None:
    key = _get_client_ip(request)
    now = time.time()
    cutoff = now - _WINDOW
    with _lock:
        _request_log[key] = [t for t in _request_log[key] if t > cutoff]
        if len(_request_log[key]) >= max_requests:
            raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
        _request_log[key].append(now)


def login_rate_limit(request: Request) -> None:
    _check(request, max_requests=5)


def signup_rate_limit(request: Request) -> None:
    _check(request, max_requests=3)
