#!/bin/sh
set -e

echo "=== ENTRYPOINT START: APP_ROLE=${APP_ROLE} ==="

if [ "$APP_ROLE" = "worker" ]; then
    echo "Starting Celery worker..."
    python healthserver.py &
    exec celery -A app.celery_app worker --pool="${CELERY_POOL:-solo}" --loglevel=info
elif [ "$APP_ROLE" = "beat" ]; then
    echo "Starting Celery beat..."
    python healthserver.py &
    exec celery -A app.celery_app beat --loglevel=info
elif [ "$1" = "api" ] || [ -z "$1" ]; then
    echo "Starting API server..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
else
    exec "$@"
fi
