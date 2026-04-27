"""
Celery application factory.
Run worker:  celery -A app.celery_app worker --loglevel=info
Run beat:    celery -A app.celery_app beat  --loglevel=info
"""

import ssl
import sys
from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "smart_reminder",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks"],
)

if settings.REDIS_SSL:
    _ssl_config = {"ssl_cert_reqs": ssl.CERT_NONE}
    celery_app.conf.broker_use_ssl = _ssl_config
    celery_app.conf.redis_backend_use_ssl = _ssl_config

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
        # Recovery-only: catches reminders whose ETA tasks were lost (Redis restart,
        # app crash between commit and apply_async, etc.). Runs every 10 minutes.
        # Normal scheduling is handled by trigger_call.apply_async(eta=...) at creation.
        "recover-missed-reminders": {
            "task": "app.tasks.recover_missed_reminders",
            "schedule": 600.0,
        },
    },
)
