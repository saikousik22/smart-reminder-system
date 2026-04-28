# Azure App Service Setup Guide

## Problem Diagnosis

Your Celery workers and beat aren't registering because:

1. **Startup commands override ENTRYPOINT**: When you set a startup command in Azure, it bypasses the Docker ENTRYPOINT, so `entrypoint.sh` was never running
2. **Health server port conflicts**: All 3 instances were trying to listen on the same port
3. **Missing worker registration**: Without proper initialization, workers don't register in Redis

## Solution: 3 App Services Setup

### For ALL 3 App Services:

1. **Build & push image to ACR** (do this locally):
   ```bash
   cd backend
   docker build -t <your-registry>.azurecr.io/smart-reminder-backend:latest .
   docker push <your-registry>.azurecr.io/smart-reminder-backend:latest
   ```

### App Service 1: API (uvicorn)

**Configuration:**
- Name: `smart-reminder-api`
- Image: `<your-registry>.azurecr.io/smart-reminder-backend:latest`
- Port: `8000`

**Startup Command:** (LEAVE EMPTY - don't set a command)

**Environment Variables:**
```
APP_ROLE=api
DB_HOST=<your-postgres-host>
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=<your-password>
DB_NAME=smart_reminder
DB_SSLMODE=require
REDIS_HOST=<your-redis-host>
REDIS_PORT=6379
REDIS_PASSWORD=<your-password>
REDIS_SSL=true
AZURE_STORAGE_CONNECTION_STRING=<your-connection-string>
AZURE_CONTAINER_NAME=audio-files
PUBLIC_BASE_URL=https://<your-domain>
CORS_ORIGINS=["https://<your-domain>"]
WEBSITES_PORT=8000
```

---

### App Service 2: Celery Worker

**Configuration:**
- Name: `smart-reminder-worker`
- Image: `<your-registry>.azurecr.io/smart-reminder-backend:latest`
- Port: `8001` (for health checks only, not used by worker)

**Startup Command:** (LEAVE EMPTY)

**Environment Variables:** (same as API, but add:)
```
APP_ROLE=worker
CELERY_POOL=solo
WEBSITES_PORT=8001
```

---

### App Service 3: Celery Beat

**Configuration:**
- Name: `smart-reminder-beat`
- Image: `<your-registry>.azurecr.io/smart-reminder-backend:latest`
- Port: `8002` (for health checks only)

**Startup Command:** (LEAVE EMPTY)

**Environment Variables:** (same as API, but add:)
```
APP_ROLE=beat
WEBSITES_PORT=8002
```

---

## Verification Steps

### 1. Check Logs

In Azure Portal → App Service → Logs (Log Analytics):

For **worker**, you should see:
```
Starting Celery worker...
[worker] celery@<hostname> ready.
```

For **beat**, you should see:
```
Starting Celery beat...
[beat] celery@<hostname> ready.
```

### 2. Run Debug Script

SSH into any app service and run:
```bash
cd /app
python debug_celery.py
```

This will show:
- Redis connection status
- Registered workers
- Redis keys (celery, kombu, etc.)

### 3. Check Health Endpoints

From your API app service:

```bash
# Redis health
curl https://<api-app>.azurewebsites.net/health/redis

# Celery health (should show registered workers)
curl https://<api-app>.azurewebsites.net/health/celery
```

Expected response when worker is running:
```json
{
  "status": "ok",
  "workers": ["celery@<hostname>"],
  "celery_redis_keys": [
    "celery",
    "_kombu.binding.celery.pidbox",
    "_kombu.binding.celeryev",
    "_kombu.binding.celery"
  ],
  "kombu_redis_keys": [...],
  "ping_error": null
}
```

---

## Troubleshooting

### Problem: Still no workers showing up

1. **Check Redis connectivity**:
   ```bash
   python debug_celery.py
   ```

2. **Verify environment variables** are set (check App Service → Configuration)

3. **Check app service logs** for errors:
   ```bash
   az webapp log tail --name smart-reminder-worker --resource-group <your-rg>
   ```

4. **Verify CELERY_POOL=solo** for App Service (prefork doesn't work in containers)

### Problem: "Connection refused" errors

1. Ensure PostgreSQL and Redis are accessible from App Service
2. Check firewall rules allow App Service
3. Verify connection strings are correct

### Problem: Worker starts but doesn't claim tasks

1. Check if tasks are registered: `python debug_celery.py`
2. Ensure `app.tasks` module is properly imported in `celery_app.py`
3. Check `include=["app.tasks"]` in `celery_app.py`

---

## Important: Do NOT Set Startup Commands

❌ **DON'T do this:**
```
docker run ... celery -A app.celery_app worker
```

✅ **DO this instead:**
```
# Leave startup command EMPTY
# Set APP_ROLE=worker in environment variables
# Let entrypoint.sh handle the rest
```

The entrypoint.sh will detect APP_ROLE and start the correct process.

---

## Commands for Local Testing

Test locally with docker-compose before deploying:

```bash
# Start all services
docker-compose up

# In another terminal, test health endpoints
curl http://localhost:8000/health/celery
curl http://localhost:8000/health/redis
```
