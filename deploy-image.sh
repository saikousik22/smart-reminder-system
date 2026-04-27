#!/bin/bash
# Deploy Smart Reminder System to Azure Container Apps
# Usage: ./deploy.sh <registry-name> <resource-group> <location>

set -e

REGISTRY_NAME=${1:-myregistry}
RESOURCE_GROUP=${2:-smart-reminder-rg}
LOCATION=${3:-eastus}
IMAGE="$REGISTRY_NAME.azurecr.io/smart-reminder:latest"

echo "🚀 Starting deployment to Azure..."
echo "Registry: $REGISTRY_NAME"
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo "Image: $IMAGE"

# Step 1: Create Resource Group
echo "📁 Creating resource group..."
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --output none || echo "Resource group already exists"

# Step 2: Create App Service Plan
echo "📋 Creating app service plan..."
az appservice plan create \
  --name "smart-reminder-plan" \
  --resource-group "$RESOURCE_GROUP" \
  --sku B2 \
  --is-linux \
  --output none 2>/dev/null || echo "Plan already exists"

# Step 3: Build Docker Image
echo "🔨 Building Docker image..."
docker build -t "$IMAGE" ./backend

# Step 4: Login to Registry
echo "🔐 Logging in to Azure Container Registry..."
az acr login --name "$REGISTRY_NAME"

# Step 5: Push Image
echo "📤 Pushing image to registry..."
docker push "$IMAGE"

# Step 6: Get Registry Credentials
REGISTRY_URL="$REGISTRY_NAME.azurecr.io"
REGISTRY_USERNAME=$(az acr credential show --name "$REGISTRY_NAME" --query "username" -o tsv)
REGISTRY_PASSWORD=$(az acr credential show --name "$REGISTRY_NAME" --query "passwords[0].value" -o tsv)

echo ""
echo "✅ Image pushed successfully!"
echo ""
echo "📝 Next steps:"
echo "1. Update environment variables in the deployment scripts below"
echo "2. Run the 3 App Service creation commands:"
echo ""
echo "   # App Service 1: FastAPI Backend"
echo "   az appservice create \\"
echo "     --resource-group $RESOURCE_GROUP \\"
echo "     --plan smart-reminder-plan \\"
echo "     --name smart-reminder-api \\"
echo "     --deployment-container-image-name $IMAGE"
echo ""
echo "   # App Service 2: Celery Worker"
echo "   az appservice create \\"
echo "     --resource-group $RESOURCE_GROUP \\"
echo "     --plan smart-reminder-plan \\"
echo "     --name smart-reminder-worker \\"
echo "     --deployment-container-image-name $IMAGE"
echo ""
echo "   # App Service 3: Celery Beat"
echo "   az appservice create \\"
echo "     --resource-group $RESOURCE_GROUP \\"
echo "     --plan smart-reminder-plan \\"
echo "     --name smart-reminder-beat \\"
echo "     --deployment-container-image-name $IMAGE"
echo ""
echo "3. See AZURE_APP_SERVICES_DEPLOY.md for full instructions"
