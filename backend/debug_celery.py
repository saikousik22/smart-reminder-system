#!/usr/bin/env python
"""
Debug script to check Celery and Redis connectivity.
Run this on your Azure app services to diagnose issues.
"""

import sys
import os
import time
import redis
from app.config import get_settings
from app.celery_app import celery_app

print("=" * 60)
print("CELERY & REDIS DEBUG")
print("=" * 60)

settings = get_settings()

# 1. Check Redis connection
print("\n[1] Testing Redis Connection...")
print(f"    Redis URL: {settings.redis_url}")

try:
    r = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
        ssl=settings.REDIS_SSL,
        ssl_cert_reqs=None,
        socket_connect_timeout=5,
    )
    r.ping()
    print("    ✓ Redis connected successfully")
except Exception as e:
    print(f"    ✗ Redis connection failed: {e}")
    sys.exit(1)

# 2. Check Celery broker connection
print("\n[2] Testing Celery Broker...")
try:
    celery_app.connection()
    print("    ✓ Celery broker connected")
except Exception as e:
    print(f"    ✗ Celery broker connection failed: {e}")

# 3. List Redis keys
print("\n[3] Redis Keys:")
try:
    all_keys = r.keys("*")
    print(f"    Total keys: {len(all_keys)}")

    celery_keys = [k.decode() for k in r.keys("*celery*") or []]
    kombu_keys = [k.decode() for k in r.keys("*kombu*") or []]

    print(f"    Celery keys: {len(celery_keys)}")
    for key in celery_keys[:10]:
        print(f"        - {key}")

    print(f"    Kombu keys: {len(kombu_keys)}")
    for key in kombu_keys[:10]:
        print(f"        - {key}")
except Exception as e:
    print(f"    ✗ Error listing keys: {e}")

# 4. Try to ping workers
print("\n[4] Pinging Celery Workers...")
try:
    inspect = celery_app.control.inspect(timeout=5)
    ping_result = inspect.ping()

    if ping_result:
        print(f"    ✓ Found {len(ping_result)} worker(s):")
        for worker_name in ping_result.keys():
            print(f"        - {worker_name}")
    else:
        print("    ✗ No workers found (this is expected if no worker is running)")
except Exception as e:
    print(f"    ✗ Error pinging workers: {e}")

# 5. Check Celery broker configuration
print("\n[5] Celery Configuration:")
print(f"    Broker: {celery_app.conf.broker_url}")
print(f"    Pool: {celery_app.conf.worker_pool}")
print(f"    Timezone: {celery_app.conf.timezone}")
print(f"    Task serializer: {celery_app.conf.task_serializer}")

# 6. Check if tasks are registered
print("\n[6] Registered Tasks:")
tasks = celery_app.tasks
task_names = [t for t in sorted(tasks.keys()) if not t.startswith("celery.")]
print(f"    Total tasks: {len(task_names)}")
for task_name in task_names:
    print(f"        - {task_name}")

print("\n" + "=" * 60)
print("Debug complete!")
print("=" * 60)
