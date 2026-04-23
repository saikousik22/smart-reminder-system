"""
Celery application factory.
Run worker:  celery -A app.celery_app worker --loglevel=info
Run beat:    celery -A app.celery_app beat  --loglevel=info
"""

import sys
from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "smart_reminder",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks"],
)

# Windows does not support the default prefork (fork-based) pool.
# 'solo' runs tasks in the main worker thread — fine for local dev.
# On Linux/macOS the default prefork pool is used instead.
_pool = "solo" if sys.platform == "win32" else "prefork"

celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    worker_pool=_pool,
    worker_concurrency=5,
    beat_schedule={
        "check-reminders-every-60s": {
            "task": "app.tasks.beat_check_reminders",
            "schedule": 60.0,
        },
    },
)
