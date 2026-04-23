"""
Simple in-memory rate limiter used as a FastAPI dependency.
Not suitable for multi-process deployments (use Redis-backed limiting there).
The threading.Lock makes the check-then-append atomic within a single process.
"""

import time
import threading
from collections import defaultdict
from fastapi import HTTPException, Request

_request_log: dict[str, list[float]] = defaultdict(list)
_lock = threading.Lock()
_WINDOW = 60.0  # seconds


def _check(request: Request, max_requests: int) -> None:
    key = request.client.host if request.client else "unknown"
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
