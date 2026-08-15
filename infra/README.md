# ForgeMind AI Azure deployment

`main.bicep` defines the complete Phase 3 Azure-native environment:

- Virtual Network with delegated Container Apps and private PostgreSQL subnets
- Azure Container Registry and user-assigned managed identity
- Azure Database for PostgreSQL Flexible Server
- Azure Blob Storage and Azure AI Search
- Microsoft Foundry/Azure OpenAI account and model deployments
- Azure Key Vault secrets referenced by the API Container App
- public Next.js Container App and private FastAPI Container App
- Application Insights and Log Analytics
- least-scope data-plane role assignments for the application identity

## Prerequisites

- An Azure subscription and selected subscription context
- Azure CLI with Bicep support
- permission to deploy resources and create role assignments
- Azure OpenAI/Foundry access and model quota in the selected AI region
- Docker is not required when images are built with ACR Tasks

The default SKUs are intended for a controlled conference environment, not a production capacity recommendation. Review current prices before deployment.

## Local two-stage deployment

```powershell
az login
az account set --subscription "<subscription-id>"

$resourceGroup = "rg-forgemind-conference"
$location = "centralindia"
$aiLocation = "eastus2"
$postgresPassword = Read-Host "PostgreSQL administrator password"
$jwtSecret = Read-Host "Long random JWT signing secret"

az group create --name $resourceGroup --location $location

# Stage 1: shared resources and ACR
az deployment group create `
  --resource-group $resourceGroup `
  --template-file infra/main.bicep `
  --parameters prefix=forgemind location=$location aiLocation=$aiLocation deployApps=false `
    postgresAdminPassword=$postgresPassword jwtSecret=$jwtSecret

$acr = az deployment group show `
  --resource-group $resourceGroup `
  --name main `
  --query properties.outputs.containerRegistryName.value -o tsv

$tag = "phase3"
az acr build --registry $acr --image "forgemind-api:$tag" --file backend/Dockerfile.azure .
az acr build --registry $acr --image "forgemind-web:$tag" --file frontend/Dockerfile.azure .

# Stage 2: Container Apps
az deployment group create `
  --resource-group $resourceGroup `
  --template-file infra/main.bicep `
  --parameters prefix=forgemind location=$location aiLocation=$aiLocation deployApps=true imageTag=$tag `
    postgresAdminPassword=$postgresPassword jwtSecret=$jwtSecret
```

Use distinct high-entropy values for the database password and JWT secret. The template stores them in Key Vault and injects them into the API with managed-identity Key Vault references.

## GitHub Actions

`.github/workflows/azure-deploy.yml` runs the same two-stage deployment with Azure OIDC. Configure:

- secrets: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `POSTGRES_ADMIN_PASSWORD`, `JWT_SECRET`
- optional variables: `AZURE_RESOURCE_GROUP`, `AZURE_LOCATION`, `AZURE_AI_LOCATION`, `FORGEMIND_PREFIX`

The workflow is manual by default to prevent accidental Azure charges. It emits the deployed frontend URL in its job summary.

## Notes

- The API ingress is internal; only the web Container App can proxy requests to it.
- PostgreSQL has public access disabled and resolves through a private DNS zone.
- Storage, Search, Foundry, and Key Vault use Microsoft Entra authentication for the application. Their public endpoints can be replaced with private endpoints in a later hardening profile.
- If the chosen AI region lacks the default model/version/SKU, override the model parameters or set `provisionModelDeployments=false`, deploy supported models, and then deploy the apps.
- No Azure resource is created merely by cloning or building this repository.
