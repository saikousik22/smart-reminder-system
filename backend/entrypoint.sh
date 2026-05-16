#!/bin/sh
set -e

echo "=== ENTRYPOINT START ==="
echo "APP_ROLE=${APP_ROLE}"
echo "Arguments: $@"
echo "CELERY_POOL=${CELERY_POOL:-}"

# Start health server for API only (runs in background for Azure health checks)
start_health_server() {
    echo "Starting health server..."
    python healthserver.py > /tmp/healthserver.log 2>&1 &
    HEALTH_PID=$!
    echo "Health server running (PID: $HEALTH_PID)"
}

# Determine what to run
# Priority: APP_ROLE env var > check command args > default to API
ROLE="${APP_ROLE:-}"

# If no APP_ROLE, check the command arguments for clues
if [ -z "$ROLE" ]; then
    if echo "$@" | grep -q "worker"; then
        ROLE="worker"
    elif echo "$@" | grep -q "beat"; then
        ROLE="beat"
    elif echo "$@" | grep -q "uvicorn"; then
        ROLE="api"
    elif [ -z "$1" ]; then
        ROLE="api"
    fi
fi

echo "Detected ROLE: $ROLE"

# Route based on role
case "$ROLE" in
    worker)
        echo "Starting Celery worker..."
        # Don't start health server for worker
        exec celery -A app.celery_app worker --pool="${CELERY_POOL:-solo}" --loglevel=info
        ;;
    beat)
        echo "Starting Celery beat..."
        # Don't start health server for beat
        exec celery -A app.celery_app beat --loglevel=info
        ;;
    api)
        echo "Starting API server..."
        exec uvicorn app.main:app --host 0.0.0.0 --port 8000
        ;;
    *)
        # Fallback: if we got here, just run whatever was passed
        echo "Running custom command: $@"
        exec "$@"
        ;;
esac
