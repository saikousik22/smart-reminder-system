# 🚀 Azure App Services Deployment Guide — 3 Services

Deploy your Smart Reminder System to Azure with 3 separate App Services:
- **App Service 1**: FastAPI Backend (runs uvicorn)
- **App Service 2**: Celery Worker
- **App Service 3**: Celery Beat

---

## 📋 Prerequisites

- Azure CLI installed and logged in: `az login`
- Docker image pushed to Azure Container Registry
- Resource Group created
- App Service Plan created

---

## 🔧 Setup Steps

### Step 1: Verify Prerequisites

```bash
# Verify you're logged in
az account show

# Create Resource Group (if needed)
az group create \
  --name smart-reminder-rg \
  --location eastus

# Create App Service Plan (if needed)
az appservice plan create \
  --name smart-reminder-plan \
  --resource-group smart-reminder-rg \
  --sku B2 \
  --is-linux
```

### Step 2: Build & Push Docker Image

```bash
# Build image
docker build -t myregistry.azurecr.io/smart-reminder:latest ./backend

# Login to Azure Container Registry
az acr login --name myregistry

# Push image
docker push myregistry.azurecr.io/smart-reminder:latest

# Verify push
az acr repository list --name myregistry
```

---

## 🏗️ Create 3 App Services

### **App Service 1: FastAPI Backend** (runs uvicorn by default)

```bash
az containerapp create \
  --resource-group smart-reminder-rg \
  --name smart-reminder-api \
  --image myregistry.azurecr.io/smart-reminder:latest \
  --cpu 0.5 \
  --memory 1.0Gi \
  --environment-variables \
    DATABASE_URL="postgresql://user:pass@host/db" \
    REDIS_URL="redis://:password@host:6379/0" \
    TWILIO_ACCOUNT_SID="ACxxxxxxx" \
    TWILIO_AUTH_TOKEN="your_token" \
    TWILIO_PHONE_NUMBER="+1234567890" \
    SECRET_KEY="your_secret_key" \
    PUBLIC_BASE_URL="https://your-api.azurewebsites.net" \
    CORS_ORIGINS='["https://your-frontend.azurestaticapps.com"]' \
  --ingress external \
  --target-port 8000 \
  --registry-server myregistry.azurecr.io \
  --registry-username myregistry \
  --registry-password "your_registry_password"
```

---

### **App Service 2: Celery Worker** (with startup command override)

```bash
az containerapp create \
  --resource-group smart-reminder-rg \
  --name smart-reminder-worker \
  --image myregistry.azurecr.io/smart-reminder:latest \
  --cpu 0.5 \
  --memory 1.0Gi \
  --environment-variables \
    DATABASE_URL="postgresql://user:pass@host/db" \
    REDIS_URL="redis://:password@host:6379/0" \
    TWILIO_ACCOUNT_SID="ACxxxxxxx" \
    TWILIO_AUTH_TOKEN="your_token" \
    TWILIO_PHONE_NUMBER="+1234567890" \
    SECRET_KEY="your_secret_key" \
  --command "celery -A app.celery_app worker --loglevel=info" \
  --ingress internal \
  --registry-server myregistry.azurecr.io \
  --registry-username myregistry \
  --registry-password "your_registry_password"
```

---

### **App Service 3: Celery Beat** (with startup command override)

```bash
az containerapp create \
  --resource-group smart-reminder-rg \
  --name smart-reminder-beat \
  --image myregistry.azurecr.io/smart-reminder:latest \
  --cpu 0.25 \
  --memory 0.5Gi \
  --environment-variables \
    DATABASE_URL="postgresql://user:pass@host/db" \
    REDIS_URL="redis://:password@host:6379/0" \
    TWILIO_ACCOUNT_SID="ACxxxxxxx" \
    TWILIO_AUTH_TOKEN="your_token" \
    TWILIO_PHONE_NUMBER="+1234567890" \
    SECRET_KEY="your_secret_key" \
  --command "celery -A app.celery_app beat --loglevel=info" \
  --ingress internal \
  --registry-server myregistry.azurecr.io \
  --registry-username myregistry \
  --registry-password "your_registry_password"
```

---

## 📊 Configuration Summary

| Service | Container App Name | Ingress | Startup Command | CPU | Memory |
|---------|-------------------|---------|-----------------|-----|--------|
| **FastAPI API** | smart-reminder-api | External (port 8000) | `None` (uses entrypoint.sh) | 0.5 | 1.0Gi |
| **Celery Worker** | smart-reminder-worker | Internal | `celery -A app.celery_app worker --loglevel=info` | 0.5 | 1.0Gi |
| **Celery Beat** | smart-reminder-beat | Internal | `celery -A app.celery_app beat --loglevel=info` | 0.25 | 0.5Gi |

---

## ✅ Verify Deployment

```bash
# List all container apps
az containerapp list --resource-group smart-reminder-rg

# Get details of API service
az containerapp show \
  --resource-group smart-reminder-rg \
  --name smart-reminder-api

# View logs
az containerapp logs show \
  --resource-group smart-reminder-rg \
  --name smart-reminder-api \
  --follow

# View worker logs
az containerapp logs show \
  --resource-group smart-reminder-rg \
  --name smart-reminder-worker \
  --follow

# View beat logs
az containerapp logs show \
  --resource-group smart-reminder-rg \
  --name smart-reminder-beat \
  --follow
```

---

## 🔍 Environment Variables Reference

Set these on **ALL 3** services:

```env
# Database
DATABASE_URL=postgresql://user:password@host:5432/smart_reminder_db

# Redis (Message Broker)
REDIS_URL=redis://:password@redis-host:6379/0

# Twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890

# Security
SECRET_KEY=your-random-secret-key-here

# URLs (set on API service only)
PUBLIC_BASE_URL=https://smart-reminder-api.azurewebsites.net
CORS_ORIGINS=["https://your-frontend-domain.azurestaticapps.com"]
```

---

## 🔄 Update Deployment

When you push a new image version:

```bash
# Pull latest image
docker pull myregistry.azurecr.io/smart-reminder:latest

# Restart all 3 services to pull new image
az containerapp update \
  --resource-group smart-reminder-rg \
  --name smart-reminder-api \
  --image myregistry.azurecr.io/smart-reminder:latest

az containerapp update \
  --resource-group smart-reminder-rg \
  --name smart-reminder-worker \
  --image myregistry.azurecr.io/smart-reminder:latest

az containerapp update \
  --resource-group smart-reminder-rg \
  --name smart-reminder-beat \
  --image myregistry.azurecr.io/smart-reminder:latest
```

---

## 📝 Key Points

✅ **Same Docker Image** used for all 3 services  
✅ **Different Startup Commands** override the entrypoint for worker and beat  
✅ **FastAPI Service** has `--ingress external` (port 8000 accessible)  
✅ **Worker & Beat** have `--ingress internal` (not exposed to internet)  
✅ **All 3 share** same database and Redis  

---

## 🛑 Stop/Delete Services

```bash
# Delete a service
az containerapp delete \
  --resource-group smart-reminder-rg \
  --name smart-reminder-api

# Delete all services
az containerapp delete \
  --resource-group smart-reminder-rg \
  --name smart-reminder-api

az containerapp delete \
  --resource-group smart-reminder-rg \
  --name smart-reminder-worker

az containerapp delete \
  --resource-group smart-reminder-rg \
  --name smart-reminder-beat
```

---

## 🎯 Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│            Azure Container Registry                          │
│   myregistry.azurecr.io/smart-reminder:latest                │
│   (Same image for all 3 services)                            │
└────────┬─────────────────────┬──────────────┬────────────────┘
         │                     │              │
    ┌────▼─────┐          ┌────▼──────┐  ┌───▼──────┐
    │ Container │          │ Container │  │Container │
    │ App 1     │          │ App 2     │  │ App 3    │
    │           │          │           │  │          │
    │ FastAPI   │          │  Worker   │  │  Beat    │
    │ (unicorn) │          │ (celery)  │  │ (celery) │
    │           │          │           │  │          │
    │ Port 8000 │          │ Internal  │  │ Internal │
    │ External  │          │           │  │          │
    │ Ingress   │          │ Ingress   │  │ Ingress  │
    └────┬──────┘          └────┬──────┘  └────┬─────┘
         │                      │              │
         └──────────────────────┼──────────────┘
                                │
                    ┌───────────┴──────────┐
                    │                      │
              ┌─────▼──────┐       ┌──────▼────┐
              │ PostgreSQL  │       │   Redis   │
              │  Database   │       │  Broker   │
              └─────────────┘       └───────────┘
```

---

## 📞 Support & Monitoring

### View Service Status
```bash
az containerapp show \
  --resource-group smart-reminder-rg \
  --name smart-reminder-api \
  --query "properties.runningStatus"
```

### View Recent Logs
```bash
# Last 100 lines
az containerapp logs show \
  --resource-group smart-reminder-rg \
  --name smart-reminder-api \
  --tail 100
```

### Health Check
```bash
# Test API health
curl https://smart-reminder-api.azurewebsites.net/

# Should return:
# {"status":"healthy","app":"Smart Reminder System","message":"..."}
```

---

**Done! Your 3-service deployment is ready.** 🚀
