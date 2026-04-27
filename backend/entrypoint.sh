#!/bin/sh
set -e

# When called with no args (or "api"), run migrations then start uvicorn.
# Any other args are executed directly (e.g. celery worker/beat).
if [ "$1" = "api" ] || [ -z "$1" ]; then
    echo "Starting API server..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
else
    exec "$@"
fi
