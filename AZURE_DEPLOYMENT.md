# Azure Deployment Guide — Smart Reminder System

## Table of Contents
1. [Architecture on Azure](#1-architecture-on-azure)
2. [Prerequisites](#2-prerequisites)
3. [Step 1 — Azure Setup & Login](#3-step-1--azure-setup--login)
4. [Step 2 — Resource Group](#4-step-2--resource-group)
5. [Step 3 — PostgreSQL Database](#5-step-3--postgresql-database)
6. [Step 4 — Redis Cache](#6-step-4--redis-cache)
7. [Step 5 — Storage Account (Audio Files)](#7-step-5--storage-account-audio-files)
8. [Step 6 — Container Registry](#8-step-6--container-registry)
9. [Step 7 — Docker Images](#9-step-7--docker-images)
10. [Step 8 — Backend App Service (FastAPI)](#10-step-8--backend-app-service-fastapi)
11. [Step 9 — Celery Worker App Service](#11-step-9--celery-worker-app-service)
12. [Step 10 — Frontend Static Web App](#12-step-10--frontend-static-web-app)
13. [Step 11 — Run Database Migrations](#13-step-11--run-database-migrations)
14. [Step 12 — Configure Twilio Webhooks](#14-step-12--configure-twilio-webhooks)
15. [Step 13 — Final Checks & Smoke Test](#15-step-13--final-checks--smoke-test)
16. [Environment Variables Reference](#16-environment-variables-reference)
17. [Dockerfiles](#17-dockerfiles)
18. [Troubleshooting](#18-troubleshooting)
19. [Cost Estimate](#19-cost-estimate)

---

## 1. Architecture on Azure

```
Internet Users
     │
     ▼
Azure Static Web App (React frontend)
     │ API calls
     ▼
Azure App Service — FastAPI Backend (Linux, Docker)
     │                    │
     │                    │ Audio files (replace local uploads/)
     │                    ▼
     │          Azure Blob Storage
     │
     ├── PostgreSQL (Azure Database for PostgreSQL Flexible)
     ├── Redis (Azure Cache for Redis)
     │
     ▼
Azure App Service — Celery Worker + Beat (Linux, Docker)
     │
     ▼
Twilio API (outbound calls + SMS)
     │ Webhooks
     ▼
FastAPI Backend (same App Service)
```

**Services used:**
| Azure Service | Purpose | SKU (min) |
|---|---|---|
| Azure Database for PostgreSQL Flexible | Database | Burstable B1ms |
| Azure Cache for Redis | Celery broker + result | C0 Basic |
| Azure Container Registry | Store Docker images | Basic |
| Azure App Service Plan (Linux) | Backend + Celery | B2 (2 vCPU, 3.5GB) |
| Azure App Service (Backend) | FastAPI API | on above plan |
| Azure App Service (Worker) | Celery worker + beat | on above plan |
| Azure Static Web App | React frontend | Free |
| Azure Blob Storage | Audio files | LRS Standard |

---

## 2. Prerequisites

Install these tools locally:

```bash
# Azure CLI
# Windows: download installer from https://aka.ms/installazurecliwindows
# Or via winget:
winget install Microsoft.AzureCLI

# Docker Desktop (for building images)
# Download from https://www.docker.com/products/docker-desktop

# Verify installations
az --version
docker --version

# Node.js (for frontend build)
node --version   # need 18+
npm --version
```

You also need:
- Azure account with an active subscription
- Twilio account with Account SID, Auth Token, and a phone number
- Your codebase (`d:\smart-reminder-system`)

---

## 3. Step 1 — Azure Setup & Login

```bash
# Login to Azure
az login

# Check your subscriptions
az account list --output table

# Set the subscription you want to use (replace with your subscription ID)
az account set --subscription "YOUR_SUBSCRIPTION_ID"

# Verify active subscription
az account show --output table
```

---

## 4. Step 2 — Resource Group

All resources go in one resource group for easy management and cleanup.

```bash
# Set variables (run these before other steps — they're used throughout)
RESOURCE_GROUP="smart-reminder-rg"
LOCATION="eastus"            # change if preferred: westus2, westeurope, etc.
APP_NAME="smart-reminder"    # base name — will prefix all resource names

# Create resource group
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION

# Verify
az group show --name $RESOURCE_GROUP --output table
```

---

## 5. Step 3 — PostgreSQL Database

```bash
# Variables
DB_SERVER_NAME="${APP_NAME}-db"      # must be globally unique
DB_ADMIN_USER="reminderadmin"
DB_ADMIN_PASSWORD="StrongPass@2026!" # CHANGE THIS — use a strong password
DB_NAME="smart_reminder"

# Create PostgreSQL Flexible Server (cheapest tier for start)
az postgres flexible-server create \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER_NAME \
  --location $LOCATION \
  --admin-user $DB_ADMIN_USER \
  --admin-password $DB_ADMIN_PASSWORD \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --version 15 \
  --public-access None

# Create the database
az postgres flexible-server db create \
  --resource-group $RESOURCE_GROUP \
  --server-name $DB_SERVER_NAME \
  --database-name $DB_NAME

# Allow Azure services to connect
az postgres flexible-server firewall-rule create \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER_NAME \
  --rule-name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0

# Get the connection string (save this!)
DB_HOST="${DB_SERVER_NAME}.postgres.database.azure.com"
DATABASE_URL="postgresql://${DB_ADMIN_USER}:${DB_ADMIN_PASSWORD}@${DB_HOST}:5432/${DB_NAME}?sslmode=require"
echo "DATABASE_URL=$DATABASE_URL"
```

---

## 6. Step 4 — Redis Cache

```bash
# Variables
REDIS_NAME="${APP_NAME}-redis"    # must be globally unique

# Create Redis Cache (C0 Basic = cheapest)
az redis create \
  --resource-group $RESOURCE_GROUP \
  --name $REDIS_NAME \
  --location $LOCATION \
  --sku Basic \
  --vm-size c0

# Wait for creation (takes ~10-15 minutes)
az redis show \
  --resource-group $RESOURCE_GROUP \
  --name $REDIS_NAME \
  --query provisioningState

# Get Redis connection details (save these!)
REDIS_HOST=$(az redis show \
  --resource-group $RESOURCE_GROUP \
  --name $REDIS_NAME \
  --query hostName --output tsv)

REDIS_KEY=$(az redis list-keys \
  --resource-group $RESOURCE_GROUP \
  --name $REDIS_NAME \
  --query primaryKey --output tsv)

REDIS_PORT="6380"
REDIS_URL="rediss://:${REDIS_KEY}@${REDIS_HOST}:${REDIS_PORT}/0"
echo "REDIS_URL=$REDIS_URL"
```

> **Note:** Azure Redis uses port 6380 with SSL (`rediss://` scheme). Port 6379 with `redis://` will NOT work.

---

## 7. Step 5 — Storage Account (Audio Files)

Audio files (currently stored in `backend/uploads/`) need to move to Azure Blob Storage for persistent, scalable storage.

```bash
# Variables
STORAGE_ACCOUNT_NAME="${APP_NAME}storage"   # lowercase, no hyphens, max 24 chars
STORAGE_ACCOUNT_NAME=$(echo $STORAGE_ACCOUNT_NAME | tr -d '-')
CONTAINER_NAME="audio-files"

# Create storage account
az storage account create \
  --name $STORAGE_ACCOUNT_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2

# Get storage connection string
STORAGE_CONNECTION_STRING=$(az storage account show-connection-string \
  --resource-group $RESOURCE_GROUP \
  --name $STORAGE_ACCOUNT_NAME \
  --query connectionString --output tsv)

# Create blob container for audio files (private access — served via SAS or CDN)
az storage container create \
  --name $CONTAINER_NAME \
  --connection-string $STORAGE_CONNECTION_STRING \
  --public-access blob    # public read so Twilio can fetch audio URLs

echo "STORAGE_CONNECTION_STRING=$STORAGE_CONNECTION_STRING"
echo "AZURE_STORAGE_CONTAINER=$CONTAINER_NAME"
```

> **Important:** After enabling Azure Blob Storage for audio, update `twilio_service.py` to use Blob Storage URLs instead of `{PUBLIC_BASE_URL}/audio/{filename}`. See [Step 12](#14-step-12--configure-twilio-webhooks) for the updated URL format.

---

## 8. Step 6 — Container Registry

```bash
# Variables
ACR_NAME="${APP_NAME}registry"         # lowercase, no hyphens
ACR_NAME=$(echo $ACR_NAME | tr -d '-')

# Create container registry
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled true

# Get registry credentials (save these!)
ACR_LOGIN_SERVER="${ACR_NAME}.azurecr.io"
ACR_USERNAME=$(az acr credential show \
  --name $ACR_NAME \
  --query username --output tsv)
ACR_PASSWORD=$(az acr credential show \
  --name $ACR_NAME \
  --query passwords[0].value --output tsv)

echo "ACR_LOGIN_SERVER=$ACR_LOGIN_SERVER"
echo "ACR_USERNAME=$ACR_USERNAME"
```

---

## 9. Step 7 — Docker Images

### Create Dockerfiles

First, create these files in your project:

**`backend/Dockerfile`** (FastAPI + Celery — same image, different CMD):
```dockerfile
FROM python:3.11-slim

# Install system dependencies including ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Default: run FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**`frontend/Dockerfile`** (Build + serve with nginx):
```dockerfile
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

# Pass build-time API URL
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**`frontend/nginx.conf`**:
```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://BACKEND_URL/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Build and Push Images

```bash
# Login to Azure Container Registry
az acr login --name $ACR_NAME

# Also login via Docker for push
docker login $ACR_LOGIN_SERVER \
  --username $ACR_USERNAME \
  --password $ACR_PASSWORD

# Build backend image
cd d:/smart-reminder-system/backend
docker build -t ${ACR_LOGIN_SERVER}/smart-reminder-backend:latest .

# Push backend image
docker push ${ACR_LOGIN_SERVER}/smart-reminder-backend:latest

# Build frontend image (replace BACKEND_URL with your actual App Service URL)
cd d:/smart-reminder-system/frontend
docker build \
  --build-arg VITE_API_URL=https://smart-reminder-api.azurewebsites.net \
  -t ${ACR_LOGIN_SERVER}/smart-reminder-frontend:latest .

# Push frontend image
docker push ${ACR_LOGIN_SERVER}/smart-reminder-frontend:latest

# Verify images in registry
az acr repository list --name $ACR_NAME --output table
```

---

## 10. Step 8 — Backend App Service (FastAPI)

```bash
# Create App Service Plan (shared between backend and worker)
APP_SERVICE_PLAN="${APP_NAME}-plan"

az appservice plan create \
  --name $APP_SERVICE_PLAN \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --is-linux \
  --sku B2

# Create Backend App Service
BACKEND_APP_NAME="${APP_NAME}-api"

az webapp create \
  --resource-group $RESOURCE_GROUP \
  --plan $APP_SERVICE_PLAN \
  --name $BACKEND_APP_NAME \
  --deployment-container-image-name ${ACR_LOGIN_SERVER}/smart-reminder-backend:latest

# Configure App Service to pull from ACR
az webapp config container set \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_APP_NAME \
  --docker-custom-image-name ${ACR_LOGIN_SERVER}/smart-reminder-backend:latest \
  --docker-registry-server-url https://${ACR_LOGIN_SERVER} \
  --docker-registry-server-user $ACR_USERNAME \
  --docker-registry-server-password $ACR_PASSWORD

# Get the backend URL (save this!)
BACKEND_URL="https://${BACKEND_APP_NAME}.azurewebsites.net"
echo "BACKEND_URL=$BACKEND_URL"

# Generate a strong JWT secret
JWT_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")
echo "JWT_SECRET_KEY=$JWT_SECRET"

# Set ALL environment variables for the backend
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_APP_NAME \
  --settings \
    APP_NAME="SmartReminderSystem" \
    DEBUG="false" \
    DATABASE_URL="$DATABASE_URL" \
    JWT_SECRET_KEY="$JWT_SECRET" \
    JWT_ALGORITHM="HS256" \
    JWT_EXPIRY_HOURS="24" \
    TWILIO_ACCOUNT_SID="YOUR_TWILIO_ACCOUNT_SID" \
    TWILIO_AUTH_TOKEN="YOUR_TWILIO_AUTH_TOKEN" \
    TWILIO_PHONE_NUMBER="YOUR_TWILIO_PHONE_NUMBER" \
    REDIS_URL="$REDIS_URL" \
    PUBLIC_BASE_URL="$BACKEND_URL" \
    CORS_ORIGINS='["https://YOUR_FRONTEND_URL.azurestaticapps.net"]' \
    COOKIE_SECURE="true" \
    AZURE_STORAGE_CONNECTION_STRING="$STORAGE_CONNECTION_STRING" \
    AZURE_STORAGE_CONTAINER="audio-files" \
    WEBSITES_PORT="8000"

# Enable continuous deployment (optional — redeploys when image is updated)
az webapp deployment container config \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_APP_NAME \
  --enable-cd true

# Restart the app
az webapp restart \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_APP_NAME

# Check app status
az webapp show \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_APP_NAME \
  --query state --output tsv

# View startup logs
az webapp log tail \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_APP_NAME
```

---

## 11. Step 9 — Celery Worker App Service

```bash
WORKER_APP_NAME="${APP_NAME}-worker"

# Create worker App Service (same plan = same server, cheaper)
az webapp create \
  --resource-group $RESOURCE_GROUP \
  --plan $APP_SERVICE_PLAN \
  --name $WORKER_APP_NAME \
  --deployment-container-image-name ${ACR_LOGIN_SERVER}/smart-reminder-backend:latest

# Configure ACR pull
az webapp config container set \
  --resource-group $RESOURCE_GROUP \
  --name $WORKER_APP_NAME \
  --docker-custom-image-name ${ACR_LOGIN_SERVER}/smart-reminder-backend:latest \
  --docker-registry-server-url https://${ACR_LOGIN_SERVER} \
  --docker-registry-server-user $ACR_USERNAME \
  --docker-registry-server-password $ACR_PASSWORD

# IMPORTANT: Override the start command to run BOTH worker AND beat in one container
# (For production at scale, run them as separate App Services)
az webapp config set \
  --resource-group $RESOURCE_GROUP \
  --name $WORKER_APP_NAME \
  --startup-file "bash -c 'celery -A app.celery_app worker --loglevel=info --pool=solo & celery -A app.celery_app beat --loglevel=info & wait'"

# Set the same environment variables as backend
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $WORKER_APP_NAME \
  --settings \
    DATABASE_URL="$DATABASE_URL" \
    JWT_SECRET_KEY="$JWT_SECRET" \
    TWILIO_ACCOUNT_SID="YOUR_TWILIO_ACCOUNT_SID" \
    TWILIO_AUTH_TOKEN="YOUR_TWILIO_AUTH_TOKEN" \
    TWILIO_PHONE_NUMBER="YOUR_TWILIO_PHONE_NUMBER" \
    REDIS_URL="$REDIS_URL" \
    PUBLIC_BASE_URL="$BACKEND_URL" \
    AZURE_STORAGE_CONNECTION_STRING="$STORAGE_CONNECTION_STRING" \
    AZURE_STORAGE_CONTAINER="audio-files" \
    DEBUG="false"

az webapp restart \
  --resource-group $RESOURCE_GROUP \
  --name $WORKER_APP_NAME

# Verify worker logs
az webapp log tail \
  --resource-group $RESOURCE_GROUP \
  --name $WORKER_APP_NAME
```

---

## 12. Step 10 — Frontend Static Web App

The simplest option is Azure Static Web Apps (free tier, global CDN, CI/CD built in).

```bash
FRONTEND_APP_NAME="${APP_NAME}-frontend"

# Option A: Deploy via Azure Static Web Apps (recommended — free CDN)
az staticwebapp create \
  --name $FRONTEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --location "eastus2" \
  --source "https://github.com/YOUR_GITHUB_USERNAME/smart-reminder-system" \
  --branch "main" \
  --app-location "frontend" \
  --output-location "dist" \
  --login-with-github

# Get frontend URL
FRONTEND_URL=$(az staticwebapp show \
  --name $FRONTEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query defaultHostname --output tsv)

echo "FRONTEND_URL=https://$FRONTEND_URL"

# Set frontend environment variable for API URL
az staticwebapp appsettings set \
  --name $FRONTEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --setting-names VITE_API_URL="$BACKEND_URL"
```

**Option B: Manual build + deploy (no GitHub needed):**

```bash
# Build frontend locally first
cd d:/smart-reminder-system/frontend

# Create .env.production with backend URL
echo "VITE_API_URL=$BACKEND_URL" > .env.production

# Build
npm install
npm run build

# Deploy dist/ folder to Static Web App
DEPLOYMENT_TOKEN=$(az staticwebapp secrets list \
  --name $FRONTEND_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.apiKey --output tsv)

# Install SWA CLI
npm install -g @azure/static-web-apps-cli

# Deploy
swa deploy ./dist \
  --deployment-token $DEPLOYMENT_TOKEN \
  --env production
```

---

## 13. Step 11 — Run Database Migrations

After the backend is running, execute Alembic migrations to create the schema.

```bash
# SSH into backend App Service (or use Kudu console)
az webapp ssh \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_APP_NAME

# Inside the SSH session:
cd /app
alembic upgrade head
exit

# Alternative: run as a one-off command
az webapp ssh \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_APP_NAME \
  --command "cd /app && alembic upgrade head"
```

**Or use Azure CLI exec command:**
```bash
az webapp config container exec \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_APP_NAME \
  --exec-command "cd /app && alembic upgrade head"
```

**Verify migrations:**
```bash
az webapp ssh \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_APP_NAME \
  --command "cd /app && alembic current"
```

---

## 14. Step 12 — Configure Twilio Webhooks

Twilio needs to POST back to your FastAPI server. Now that you have a public URL:

1. **Login to Twilio Console**: https://console.twilio.com

2. **Go to Phone Numbers → Manage → Active Numbers**

3. **Click your phone number** → configure:
   - Voice webhook URL: `https://YOUR_BACKEND.azurewebsites.net/voice/{reminder_id}`
   - Status callback URL: `https://YOUR_BACKEND.azurewebsites.net/voice/status/{reminder_id}`
   - HTTP Method: POST

4. **Update PUBLIC_BASE_URL** in backend App Service settings (it should already be set):
```bash
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_APP_NAME \
  --settings PUBLIC_BASE_URL="https://${BACKEND_APP_NAME}.azurewebsites.net"
```

5. **Update CORS_ORIGINS** with actual frontend URL:
```bash
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_APP_NAME \
  --settings CORS_ORIGINS="[\"https://$FRONTEND_URL\"]"

az webapp restart \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_APP_NAME
```

---

## 15. Step 13 — Final Checks & Smoke Test

```bash
# 1. Check backend health
curl https://${BACKEND_APP_NAME}.azurewebsites.net/docs
# Should see FastAPI Swagger UI

# 2. Test auth signup
curl -X POST https://${BACKEND_APP_NAME}.azurewebsites.net/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"password123"}'

# 3. Test auth login
curl -X POST https://${BACKEND_APP_NAME}.azurewebsites.net/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
# Copy the access_token

# 4. Test authenticated endpoint
curl https://${BACKEND_APP_NAME}.azurewebsites.net/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# 5. Check frontend is loading
curl https://${FRONTEND_URL}
# Should return HTML

# 6. Check worker is processing (look at logs)
az webapp log tail \
  --resource-group $RESOURCE_GROUP \
  --name $WORKER_APP_NAME \
  --provider http

# 7. Verify Redis connection
az webapp log tail \
  --resource-group $RESOURCE_GROUP \
  --name $WORKER_APP_NAME
# Look for: "celery@... ready." and "beat: Starting..."
```

---

## 16. Environment Variables Reference

### Backend App Service Settings (set via CLI or Azure Portal)

```
APP_NAME=SmartReminderSystem
DEBUG=false
DATABASE_URL=postgresql://reminderadmin:PASSWORD@SERVER.postgres.database.azure.com:5432/smart_reminder?sslmode=require
JWT_SECRET_KEY=<64-char random hex>
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=24
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx
REDIS_URL=rediss://:KEY@NAME.redis.cache.windows.net:6380/0
PUBLIC_BASE_URL=https://smart-reminder-api.azurewebsites.net
CORS_ORIGINS=["https://YOUR-APP.azurestaticapps.net"]
COOKIE_SECURE=true
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
AZURE_STORAGE_CONTAINER=audio-files
WEBSITES_PORT=8000
```

### Frontend Build Environment

```
VITE_API_URL=https://smart-reminder-api.azurewebsites.net
```

---

## 17. Dockerfiles

Save these files before building images.

### `backend/Dockerfile`
```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/docs || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `frontend/Dockerfile`
```dockerfile
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --silent

COPY . .

ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

FROM nginx:1.25-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s CMD wget -q --spider http://localhost/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
```

### `frontend/nginx.conf`
```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    gzip on;
    gzip_types text/plain application/javascript text/css application/json;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

---

## 18. Troubleshooting

### Backend won't start
```bash
# View detailed logs
az webapp log tail \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_APP_NAME

# Check container logs
az webapp log download \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_APP_NAME \
  --log-file logs.zip

# Common fix: check WEBSITES_PORT=8000 is set
az webapp config appsettings list \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_APP_NAME \
  --output table | grep PORT
```

### Database connection fails
```bash
# Verify firewall allows Azure services
az postgres flexible-server firewall-rule list \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER_NAME \
  --output table

# Test connection from App Service SSH
az webapp ssh --resource-group $RESOURCE_GROUP --name $BACKEND_APP_NAME
# Inside: psql $DATABASE_URL -c "SELECT 1;"
```

### Redis connection fails (SSL error)
```bash
# Must use rediss:// (with double s) for Azure Redis port 6380
# Wrong:  redis://host:6379
# Correct: rediss://:password@host:6380/0
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_APP_NAME \
  --settings REDIS_URL="rediss://:$REDIS_KEY@$REDIS_HOST:6380/0"
```

### Celery worker not processing tasks
```bash
# Check worker logs
az webapp log tail \
  --resource-group $RESOURCE_GROUP \
  --name $WORKER_APP_NAME

# Celery requires --pool=solo on Azure App Service (single process)
# Verify startup command
az webapp config show \
  --resource-group $RESOURCE_GROUP \
  --name $WORKER_APP_NAME \
  --query appCommandLine --output tsv
```

### Twilio webhooks failing (voice not firing)
```bash
# 1. Verify PUBLIC_BASE_URL is the correct public HTTPS URL
# 2. Check the URL is reachable from internet
curl -v https://${BACKEND_APP_NAME}.azurewebsites.net/voice/1

# 3. Check Twilio error logs in Twilio Console
# Dashboard → Monitor → Errors

# 4. Make sure COOKIE_SECURE=true and HTTPS is enforced
# App Service enforces HTTPS by default — no extra config needed
```

### CORS errors in browser
```bash
# Update CORS_ORIGINS to match frontend URL exactly (no trailing slash)
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_APP_NAME \
  --settings CORS_ORIGINS='["https://EXACT-FRONTEND-URL.azurestaticapps.net"]'

az webapp restart --resource-group $RESOURCE_GROUP --name $BACKEND_APP_NAME
```

### Alembic migration fails
```bash
# Check current migration state
az webapp ssh --resource-group $RESOURCE_GROUP --name $BACKEND_APP_NAME
cd /app
alembic history
alembic current

# If needed, stamp current head manually
alembic stamp head
```

### Audio files not served (404 on /audio/)
```bash
# If using local uploads/ directory (not Blob Storage), verify mount
# Azure App Service filesystem is ephemeral — files lost on restart
# MUST migrate to Azure Blob Storage for production

# Quick test: upload a file and check
curl -X POST https://${BACKEND_APP_NAME}.azurewebsites.net/reminders \
  -H "Authorization: Bearer TOKEN" \
  -F "audio_file=@test.wav" \
  -F "title=test" \
  -F "phone_number=+1234567890" \
  -F "scheduled_time=2026-12-01T10:00:00"
```

---

## 19. Cost Estimate

Monthly estimated cost (USD) for minimum viable deployment:

| Service | SKU | Est. $/month |
|---|---|---|
| App Service Plan B2 | 2 vCPU, 3.5GB | ~$73 |
| PostgreSQL Flexible B1ms | 1 vCPU, 2GB | ~$25 |
| Azure Cache for Redis C0 | 250MB | ~$16 |
| Azure Container Registry Basic | 10GB | ~$5 |
| Azure Blob Storage | LRS, 10GB | ~$0.50 |
| Azure Static Web App | Free | $0 |
| **Total** | | **~$120/month** |

> To reduce costs in dev/testing: stop the App Services when not in use.
> ```bash
> az webapp stop --resource-group $RESOURCE_GROUP --name $BACKEND_APP_NAME
> az webapp stop --resource-group $RESOURCE_GROUP --name $WORKER_APP_NAME
> # Start when needed:
> az webapp start --resource-group $RESOURCE_GROUP --name $BACKEND_APP_NAME
> az webapp start --resource-group $RESOURCE_GROUP --name $WORKER_APP_NAME
> ```

---

## Quick Reference — All Variables to Save

After completing the setup steps, save these values securely:

```bash
RESOURCE_GROUP="smart-reminder-rg"
LOCATION="eastus"
APP_NAME="smart-reminder"
DB_SERVER_NAME="${APP_NAME}-db"
DB_HOST="${DB_SERVER_NAME}.postgres.database.azure.com"
DB_ADMIN_USER="reminderadmin"
DB_ADMIN_PASSWORD="<your password>"
DB_NAME="smart_reminder"
DATABASE_URL="postgresql://${DB_ADMIN_USER}:${DB_ADMIN_PASSWORD}@${DB_HOST}:5432/${DB_NAME}?sslmode=require"
REDIS_NAME="${APP_NAME}-redis"
REDIS_HOST="${REDIS_NAME}.redis.cache.windows.net"
REDIS_KEY="<from az redis list-keys>"
REDIS_URL="rediss://:${REDIS_KEY}@${REDIS_HOST}:6380/0"
ACR_NAME="${APP_NAME}registry"
ACR_LOGIN_SERVER="${ACR_NAME}.azurecr.io"
STORAGE_ACCOUNT_NAME="<your storage account>"
BACKEND_APP_NAME="${APP_NAME}-api"
WORKER_APP_NAME="${APP_NAME}-worker"
FRONTEND_APP_NAME="${APP_NAME}-frontend"
BACKEND_URL="https://${BACKEND_APP_NAME}.azurewebsites.net"
JWT_SECRET="<64-char hex>"
```
