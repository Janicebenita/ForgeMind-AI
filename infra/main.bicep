targetScope = 'resourceGroup'

@description('Short lowercase prefix used in globally unique Azure resource names.')
@minLength(3)
@maxLength(12)
param prefix string = 'forgemind'

@description('Primary Azure region for ForgeMind AI. Model availability can require a different aiLocation.')
param location string = resourceGroup().location

@description('Azure region used for the Microsoft Foundry resource and deployments.')
param aiLocation string = location

@description('Deploy the frontend and backend after their images have been built in ACR.')
param deployApps bool = false

@description('Provision the configured chat and embedding model deployments. Disable if regional quota is not ready.')
param provisionModelDeployments bool = true

@description('Container image tag built by the deployment script.')
param imageTag string = 'phase3'

@description('Azure AI Search SKU.')
@allowed([
  'basic'
  'standard'
])
param searchSku string = 'basic'

@description('PostgreSQL administrator login name.')
param postgresAdminUser string = 'forgemindadmin'

@secure()
@description('PostgreSQL administrator password. Supply it through a secure parameter or deployment secret.')
param postgresAdminPassword string

@secure()
@description('JWT signing secret for the ForgeMind API.')
param jwtSecret string

@description('PostgreSQL compute SKU for the conference environment.')
param postgresSkuName string = 'Standard_B1ms'

@description('Microsoft Foundry chat deployment name.')
param chatDeploymentName string = 'gpt-4.1-mini'

@description('Microsoft Foundry chat model name.')
param chatModelName string = 'gpt-4.1-mini'

@description('Microsoft Foundry chat model version. Confirm regional availability before deployment.')
param chatModelVersion string = '2025-04-14'

@description('Microsoft Foundry embedding deployment name.')
param embeddingDeploymentName string = 'text-embedding-3-small'

@description('Microsoft Foundry embedding model name.')
param embeddingModelName string = 'text-embedding-3-small'

@description('Microsoft Foundry embedding model version.')
param embeddingModelVersion string = '1'

var suffix = take(uniqueString(subscription().subscriptionId, resourceGroup().id), 8)
var compactPrefix = take(toLower(replace(prefix, '-', '')), 12)
var storageName = take('${compactPrefix}${suffix}st', 24)
var searchName = '${compactPrefix}-search-${suffix}'
var logName = '${compactPrefix}-logs-${suffix}'
var insightsName = '${compactPrefix}-insights-${suffix}'
var identityName = '${compactPrefix}-app-${suffix}'
var registryName = take('${compactPrefix}${suffix}acr', 50)
var environmentName = '${compactPrefix}-env-${suffix}'
var frontendName = '${compactPrefix}-web-${suffix}'
var backendName = '${compactPrefix}-api-${suffix}'
var keyVaultName = take('${compactPrefix}-${suffix}-kv', 24)
var postgresName = take('${compactPrefix}-${suffix}-pg', 63)
var foundryName = take('${compactPrefix}-${suffix}-ai', 64)
var privateDnsZoneName = '${compactPrefix}.postgres.database.azure.com'

var storageBlobDataContributorRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
var searchServiceContributorRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7ca78c08-252a-4471-8644-bb5ff32d4ba0')
var searchIndexDataContributorRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '8ebe5a00-799e-43f5-93ac-243d3dce84a7')
var acrPullRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
var keyVaultSecretsUserRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
var openAIUserRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')

resource appIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
}

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: '${compactPrefix}-vnet-${suffix}'
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.40.0.0/16'
      ]
    }
  }
}

resource containerAppsSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' = {
  parent: vnet
  name: 'container-apps'
  properties: {
    addressPrefix: '10.40.0.0/23'
    delegations: [
      {
        name: 'container-apps-delegation'
        properties: {
          serviceName: 'Microsoft.App/environments'
        }
      }
    ]
  }
}

resource postgresSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' = {
  parent: vnet
  name: 'postgresql'
  properties: {
    addressPrefix: '10.40.2.0/24'
    delegations: [
      {
        name: 'postgres-flexible-delegation'
        properties: {
          serviceName: 'Microsoft.DBforPostgreSQL/flexibleServers'
        }
      }
    ]
  }
}

resource postgresDns 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: privateDnsZoneName
  location: 'global'
}

resource postgresDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: postgresDns
  name: '${compactPrefix}-postgres-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2025-01-01' = {
  name: storageName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowCrossTenantReplication: false
    allowSharedKeyAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2025-01-01' = {
  parent: storage
  name: 'default'
}

resource documents 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-01-01' = {
  parent: blobService
  name: 'forgemind-documents'
  properties: {
    publicAccess: 'None'
  }
}

resource search 'Microsoft.Search/searchServices@2023-11-01' = {
  name: searchName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: searchSku
  }
  properties: {
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
    disableLocalAuth: true
    hostingMode: 'default'
    partitionCount: 1
    publicNetworkAccess: 'enabled'
    replicaCount: 1
    semanticSearch: 'free'
  }
}

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: registryName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
    dataEndpointEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enablePurgeProtection: true
    enableRbacAuthorization: true
    publicNetworkAccess: 'Enabled'
    softDeleteRetentionInDays: 90
  }
}

resource postgresPasswordSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'postgres-admin-password'
  properties: {
    value: postgresAdminPassword
  }
}

resource jwtSecretResource 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'jwt-signing-secret'
  properties: {
    value: jwtSecret
  }
}

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: postgresName
  location: location
  sku: {
    name: postgresSkuName
    tier: 'Burstable'
  }
  properties: {
    administratorLogin: postgresAdminUser
    administratorLoginPassword: postgresAdminPassword
    version: '16'
    authConfig: {
      activeDirectoryAuth: 'Disabled'
      passwordAuth: 'Enabled'
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    network: {
      delegatedSubnetResourceId: postgresSubnet.id
      privateDnsZoneArmResourceId: postgresDns.id
      publicNetworkAccess: 'Disabled'
    }
    storage: {
      autoGrow: 'Enabled'
      storageSizeGB: 32
    }
  }
  dependsOn: [
    postgresDnsLink
  ]
}

resource forgeMindDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: postgres
  name: 'forgemind'
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

resource logs 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logName
  location: location
  properties: {
    retentionInDays: 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

resource insights 'Microsoft.Insights/components@2020-02-02' = {
  name: insightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    RetentionInDays: 90
    WorkspaceResourceId: logs.id
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

resource foundry 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: foundryName
  location: aiLocation
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: foundryName
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

resource chatDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = if (provisionModelDeployments) {
  parent: foundry
  name: chatDeploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: chatModelName
      version: chatModelVersion
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
  }
}

resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = if (provisionModelDeployments) {
  parent: foundry
  name: embeddingDeploymentName
  sku: {
    name: 'Standard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: embeddingModelName
      version: embeddingModelVersion
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
  }
}

resource containerEnvironment 'Microsoft.App/managedEnvironments@2025-01-01' = {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
    vnetConfiguration: {
      infrastructureSubnetId: containerAppsSubnet.id
      internal: false
    }
    zoneRedundant: false
  }
}

resource blobDataRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(documents.id, appIdentity.id, storageBlobDataContributorRoleId)
  scope: documents
  properties: {
    roleDefinitionId: storageBlobDataContributorRoleId
    principalId: appIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource searchServiceRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, appIdentity.id, searchServiceContributorRoleId)
  scope: search
  properties: {
    roleDefinitionId: searchServiceContributorRoleId
    principalId: appIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource searchDataRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, appIdentity.id, searchIndexDataContributorRoleId)
  scope: search
  properties: {
    roleDefinitionId: searchIndexDataContributorRoleId
    principalId: appIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource registryPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, appIdentity.id, acrPullRoleId)
  scope: registry
  properties: {
    roleDefinitionId: acrPullRoleId
    principalId: appIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource keyVaultSecretsRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, appIdentity.id, keyVaultSecretsUserRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: keyVaultSecretsUserRoleId
    principalId: appIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource foundryUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundry.id, appIdentity.id, openAIUserRoleId)
  scope: foundry
  properties: {
    roleDefinitionId: openAIUserRoleId
    principalId: appIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource backend 'Microsoft.App/containerApps@2025-01-01' = if (deployApps) {
  name: backendName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${appIdentity.id}': {}
    }
  }
  properties: {
    environmentId: containerEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        allowInsecure: false
        external: false
        targetPort: 8000
        transport: 'auto'
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      registries: [
        {
          server: registry.properties.loginServer
          identity: appIdentity.id
        }
      ]
      secrets: [
        {
          name: 'postgres-password'
          keyVaultUrl: postgresPasswordSecret.properties.secretUri
          identity: appIdentity.id
        }
        {
          name: 'jwt-secret'
          keyVaultUrl: jwtSecretResource.properties.secretUri
          identity: appIdentity.id
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'forgemind-api'
          image: '${registry.properties.loginServer}/forgemind-api:${imageTag}'
          env: [
            { name: 'ENVIRONMENT', value: 'production' }
            { name: 'SEED_DEMO_ON_STARTUP', value: 'true' }
            { name: 'AI_PROVIDER', value: 'azure' }
            { name: 'RETRIEVAL_BACKEND', value: 'azure_search' }
            { name: 'DOCUMENT_STORAGE_BACKEND', value: 'azure_blob' }
            { name: 'POSTGRES_HOST', value: postgres.properties.fullyQualifiedDomainName }
            { name: 'POSTGRES_PORT', value: '5432' }
            { name: 'POSTGRES_DATABASE', value: 'forgemind' }
            { name: 'POSTGRES_USER', value: postgresAdminUser }
            { name: 'POSTGRES_PASSWORD', secretRef: 'postgres-password' }
            { name: 'POSTGRES_SSLMODE', value: 'require' }
            { name: 'JWT_SECRET', secretRef: 'jwt-secret' }
            { name: 'AZURE_OPENAI_ENDPOINT', value: 'https://${foundryName}.openai.azure.com' }
            { name: 'AZURE_OPENAI_CHAT_DEPLOYMENT', value: chatDeploymentName }
            { name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT', value: embeddingDeploymentName }
            { name: 'AZURE_SEARCH_ENDPOINT', value: 'https://${search.name}.search.windows.net' }
            { name: 'AZURE_SEARCH_INDEX_NAME', value: 'forgemind-chunks' }
            { name: 'AZURE_SEARCH_VECTOR_DIMENSIONS', value: '1536' }
            { name: 'AZURE_STORAGE_ACCOUNT_URL', value: 'https://${storage.name}.blob.${environment().suffixes.storage}' }
            { name: 'AZURE_STORAGE_CONTAINER', value: documents.name }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: insights.properties.ConnectionString }
            { name: 'OTEL_SERVICE_NAME', value: 'forgemind-api' }
            { name: 'AZURE_CLIENT_ID', value: appIdentity.properties.clientId }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/api/health'
                port: 8000
                scheme: 'HTTP'
              }
              initialDelaySeconds: 20
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/api/health'
                port: 8000
                scheme: 'HTTP'
              }
              initialDelaySeconds: 10
              periodSeconds: 10
            }
          ]
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
  dependsOn: [
    blobDataRole
    searchServiceRole
    searchDataRole
    registryPullRole
    keyVaultSecretsRole
    foundryUserRole
  ]
}

resource frontend 'Microsoft.App/containerApps@2025-01-01' = if (deployApps) {
  name: frontendName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${appIdentity.id}': {}
    }
  }
  properties: {
    environmentId: containerEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        allowInsecure: false
        external: true
        targetPort: 3000
        transport: 'auto'
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      registries: [
        {
          server: registry.properties.loginServer
          identity: appIdentity.id
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'forgemind-web'
          image: '${registry.properties.loginServer}/forgemind-web:${imageTag}'
          env: [
            { name: 'BACKEND_API_URL', value: 'https://${backend!.properties.configuration.ingress.fqdn}' }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/'
                port: 3000
                scheme: 'HTTP'
              }
              initialDelaySeconds: 20
              periodSeconds: 30
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
  dependsOn: [
    registryPullRole
  ]
}

output azureSearchEndpoint string = 'https://${search.name}.search.windows.net'
output storageAccountUrl string = 'https://${storage.name}.blob.${environment().suffixes.storage}'
output storageContainerName string = documents.name
output applicationInsightsConnectionString string = insights.properties.ConnectionString
output applicationIdentityId string = appIdentity.id
output applicationIdentityClientId string = appIdentity.properties.clientId
output applicationIdentityPrincipalId string = appIdentity.properties.principalId
output containerRegistryName string = registry.name
output containerRegistryServer string = registry.properties.loginServer
output postgresHost string = postgres.properties.fullyQualifiedDomainName
output keyVaultName string = keyVault.name
output foundryEndpoint string = 'https://${foundryName}.openai.azure.com'
output frontendUrl string = deployApps ? 'https://${frontend!.properties.configuration.ingress.fqdn}' : ''
output backendInternalFqdn string = deployApps ? backend!.properties.configuration.ingress.fqdn : ''
