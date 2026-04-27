# Deploy Smart Reminder System to Azure Container Apps (Windows PowerShell)
# Usage: .\deploy.ps1 -RegistryName "myregistry" -ResourceGroup "smart-reminder-rg" -Location "eastus"

param(
    [string]$RegistryName = "myregistry",
    [string]$ResourceGroup = "smart-reminder-rg",
    [string]$Location = "eastus"
)

$Image = "$RegistryName.azurecr.io/smart-reminder:latest"

Write-Host "🚀 Starting deployment to Azure..." -ForegroundColor Green
Write-Host "Registry: $RegistryName"
Write-Host "Resource Group: $ResourceGroup"
Write-Host "Location: $Location"
Write-Host "Image: $Image"
Write-Host ""

# Step 1: Create Resource Group
Write-Host "📁 Creating resource group..." -ForegroundColor Yellow
try {
    az group create `
      --name $ResourceGroup `
      --location $Location `
      --output none
    Write-Host "✅ Resource group created" -ForegroundColor Green
}
catch {
    Write-Host "⚠️  Resource group already exists" -ForegroundColor Yellow
}

# Step 2: Create App Service Plan
Write-Host "📋 Creating app service plan..." -ForegroundColor Yellow
try {
    az appservice plan create `
      --name "smart-reminder-plan" `
      --resource-group $ResourceGroup `
      --sku B2 `
      --is-linux `
      --output none
    Write-Host "✅ App Service plan created" -ForegroundColor Green
}
catch {
    Write-Host "⚠️  Plan already exists" -ForegroundColor Yellow
}

# Step 3: Build Docker Image
Write-Host "🔨 Building Docker image..." -ForegroundColor Yellow
docker build -t $Image ./backend
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Docker image built" -ForegroundColor Green
}
else {
    Write-Host "❌ Docker build failed" -ForegroundColor Red
    exit 1
}

# Step 4: Login to Registry
Write-Host "🔐 Logging in to Azure Container Registry..." -ForegroundColor Yellow
az acr login --name $RegistryName
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Logged in to registry" -ForegroundColor Green
}
else {
    Write-Host "❌ Registry login failed" -ForegroundColor Red
    exit 1
}

# Step 5: Push Image
Write-Host "📤 Pushing image to registry..." -ForegroundColor Yellow
docker push $Image
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Image pushed successfully" -ForegroundColor Green
}
else {
    Write-Host "❌ Docker push failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ Image pushed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Next steps:" -ForegroundColor Yellow
Write-Host "1. Update environment variables in Azure Portal"
Write-Host "2. See QUICK_DEPLOY_REFERENCE.md for App Service creation commands"
Write-Host ""
Write-Host "👉 Create 3 App Services:" -ForegroundColor Cyan
Write-Host ""
Write-Host "   # App Service 1: FastAPI Backend" -ForegroundColor Gray
Write-Host "   az appservice create \`" -ForegroundColor Gray
Write-Host "     --resource-group $ResourceGroup \`" -ForegroundColor Gray
Write-Host "     --plan smart-reminder-plan \`" -ForegroundColor Gray
Write-Host "     --name smart-reminder-api \`" -ForegroundColor Gray
Write-Host "     --deployment-container-image-name $Image" -ForegroundColor Gray
Write-Host ""
Write-Host "   # App Service 2: Celery Worker (with startup command)" -ForegroundColor Gray
Write-Host "   az appservice create \`" -ForegroundColor Gray
Write-Host "     --resource-group $ResourceGroup \`" -ForegroundColor Gray
Write-Host "     --plan smart-reminder-plan \`" -ForegroundColor Gray
Write-Host "     --name smart-reminder-worker \`" -ForegroundColor Gray
Write-Host "     --deployment-container-image-name $Image" -ForegroundColor Gray
Write-Host ""
Write-Host "   # App Service 3: Celery Beat (with startup command)" -ForegroundColor Gray
Write-Host "   az appservice create \`" -ForegroundColor Gray
Write-Host "     --resource-group $ResourceGroup \`" -ForegroundColor Gray
Write-Host "     --plan smart-reminder-plan \`" -ForegroundColor Gray
Write-Host "     --name smart-reminder-beat \`" -ForegroundColor Gray
Write-Host "     --deployment-container-image-name $Image" -ForegroundColor Gray
Write-Host ""
Write-Host "🔗 See AZURE_APP_SERVICES_DEPLOY.md for full instructions" -ForegroundColor Cyan
