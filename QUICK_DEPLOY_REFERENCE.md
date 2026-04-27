# Quick Reference: 3 App Services with Startup Commands

## Architecture
```
Same Docker Image → 3 Container Apps with Different Startup Commands
```

---

## 1️⃣ FastAPI Backend
**Name:** smart-reminder-api  
**Startup Command:** (none - uses default entrypoint.sh)  
**Ingress:** External (port 8000)  

```bash
az appservice create \
  --resource-group smart-reminder-rg \
  --plan smart-reminder-plan \
  --name smart-reminder-api \
  --deployment-container-image-name myregistry.azurecr.io/smart-reminder:latest
```

---

## 2️⃣ Celery Worker
**Name:** smart-reminder-worker  
**Startup Command:** `celery -A app.celery_app worker --loglevel=info`  
**Ingress:** Internal (no external access)  

```bash
az appservice create \
  --resource-group smart-reminder-rg \
  --plan smart-reminder-plan \
  --name smart-reminder-worker \
  --deployment-container-image-name myregistry.azurecr.io/smart-reminder:latest
  
# Then set startup command via Azure Portal or:
az appservice config container set \
  --resource-group smart-reminder-rg \
  --name smart-reminder-worker \
  --docker-custom-image-name myregistry.azurecr.io/smart-reminder:latest \
  --docker-registry-server-url https://myregistry.azurecr.io \
  --startup-command "celery -A app.celery_app worker --loglevel=info"
```

---

## 3️⃣ Celery Beat
**Name:** smart-reminder-beat  
**Startup Command:** `celery -A app.celery_app beat --loglevel=info`  
**Ingress:** Internal (no external access)  

```bash
az appservice create \
  --resource-group smart-reminder-rg \
  --plan smart-reminder-plan \
  --name smart-reminder-beat \
  --deployment-container-image-name myregistry.azurecr.io/smart-reminder:latest

# Then set startup command:
az appservice config container set \
  --resource-group smart-reminder-rg \
  --name smart-reminder-beat \
  --docker-custom-image-name myregistry.azurecr.io/smart-reminder:latest \
  --docker-registry-server-url https://myregistry.azurecr.io \
  --startup-command "celery -A app.celery_app beat --loglevel=info"
```

---

## Summary Table

| Service | Command Override | Purpose |
|---------|-----------------|---------|
| **API** | ❌ None | Uses `entrypoint.sh` → Runs uvicorn |
| **Worker** | ✅ Yes | `celery ... worker` → Executes tasks |
| **Beat** | ✅ Yes | `celery ... beat` → Recovery scheduler |

**Same image for all → Different startup commands = Different processes**

---

See AZURE_APP_SERVICES_DEPLOY.md for full guide
