"""
Celery application factory.
Run worker:  celery -A app.celery_app worker --loglevel=info
Run beat:    celery -A app.celery_app beat  --loglevel=info
"""

import sys
import os
import ssl
from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "smart_reminder",
    broker=settings.redis_url,
    backend=None,
    include=["app.tasks"],
)

if settings.REDIS_SSL:
    celery_app.conf.broker_use_ssl = {
        "ssl_cert_reqs": ssl.CERT_NONE,
        "ssl_check_hostname": False,
    }

# CELERY_POOL env var overrides the pool (set to "solo" on Azure App Service
# where prefork/fork-based pools fail due to container process restrictions).
_default_pool = "solo" if sys.platform == "win32" else "prefork"
_pool = os.environ.get("CELERY_POOL", _default_pool)

celery_app.conf.update(
    task_ignore_result=True,
    timezone="UTC",
    enable_utc=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    worker_pool=_pool,
    worker_concurrency=5,
    broker_connection_retry_on_startup=True,
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
