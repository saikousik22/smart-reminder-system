#!/usr/bin/env python
"""
Quick validation that the app can start without import/config errors.
Run this before deploying to Azure.
"""

import sys
import os

print("[1/4] Testing configuration loading...")
try:
    from app.config import get_settings
    settings = get_settings()
    print("    ✓ Configuration loaded")
except Exception as e:
    print(f"    ✗ Configuration failed: {e}")
    sys.exit(1)

print("[2/4] Testing database configuration...")
try:
    from app.database import SessionLocal
    from app.models import Base
    db = SessionLocal()
    db.close()
    print("    ✓ Database connection (config) OK")
except Exception as e:
    print(f"    ✗ Database config failed: {e}")
    sys.exit(1)

print("[3/4] Testing Celery initialization...")
try:
    from app.celery_app import celery_app
    print(f"    ✓ Celery app initialized")
    print(f"      Broker: {celery_app.conf.broker_url}")
    print(f"      Worker pool: {celery_app.conf.worker_pool}")
except Exception as e:
    print(f"    ✗ Celery initialization failed: {e}")
    sys.exit(1)

print("[4/4] Testing task registration...")
try:
    from app import tasks
    task_names = [t for t in celery_app.tasks.keys() if not t.startswith("celery.")]
    print(f"    ✓ Tasks registered: {len(task_names)} tasks")
    for task in task_names:
        print(f"      - {task}")
except Exception as e:
    print(f"    ✗ Task registration failed: {e}")
    sys.exit(1)

print("\n✓ All checks passed! App should work in Azure.")
