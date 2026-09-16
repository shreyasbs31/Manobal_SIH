targetScope = 'resourceGroup'
param location string = resourceGroup().location
param prefix string = 'manobal'
param environmentName string = 'demo'
param webHost string = 'localhost'
param costCapInr int = 400

var tags = {
  product: 'manobal'
  environment: environmentName
}

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${prefix}-logs'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${prefix}-insights'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

resource engineIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-id-engine'
  location: location
  tags: tags
}

resource vaultIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-id-vault'
  location: location
  tags: tags
}

resource webIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-id-web'
  location: location
  tags: tags
}

resource githubIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-id-github'
  location: location
  tags: tags
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: take('${prefix}kv${uniqueString(resourceGroup().id)}', 24)
  location: location
  tags: tags
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
  }
}

resource engineKvRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, engineIdentity.id, 'secrets')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
    principalId: engineIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource vaultKvRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, vaultIdentity.id, 'crypto')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '12338af0-0e69-4776-bea7-57ae8d297424')
    principalId: vaultIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource coreDb 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: '${prefix}-core-pg'
  location: location
  tags: tags
  sku: { name: 'Standard_B2s', tier: 'Burstable' }
  properties: {
    version: '16'
    storage: { storageSizeGB: 32 }
    authConfig: { activeDirectoryAuth: 'Enabled', passwordAuth: 'Disabled' }
  }
}

resource vaultDb 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: '${prefix}-vault-pg'
  location: location
  tags: tags
  sku: { name: 'Standard_B2s', tier: 'Burstable' }
  properties: {
    version: '16'
    storage: { storageSizeGB: 32 }
    authConfig: { activeDirectoryAuth: 'Enabled', passwordAuth: 'Disabled' }
  }
}

resource redis 'Microsoft.Cache/redis@2024-03-01' = {
  name: take('${prefix}-redis', 63)
  location: location
  tags: tags
  properties: {
    sku: { name: 'Basic', family: 'C', capacity: 0 }
    enableNonSslPort: false
    redisVersion: '6'
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: take('${prefix}audit${uniqueString(resourceGroup().id)}', 24)
  location: location
  tags: tags
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
  }
}

resource env 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${prefix}-cae'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
      }
    }
  }
}

resource engineApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${prefix}-engine'
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${engineIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      ingress: { external: true, targetPort: 8000 }
    }
    template: {
      containers: [
        {
          name: 'engine'
          image: 'manobal/engine:local'
        }
      ]
    }
  }
}

resource vaultApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${prefix}-vault'
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${vaultIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      ingress: { external: false, targetPort: 8100 }
    }
    template: {
      containers: [
        {
          name: 'vault'
          image: 'manobal/vault:local'
        }
      ]
    }
  }
}

resource webApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${prefix}-web'
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${webIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      ingress: { external: true, targetPort: 3000 }
    }
    template: {
      containers: [
        {
          name: 'web'
          image: 'manobal/web:local'
        }
      ]
    }
  }
}

resource realtimeApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${prefix}-realtime'
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      ingress: { external: true, targetPort: 8080, transport: 'http' }
    }
    template: {
      containers: [
        {
          name: 'realtime'
          image: 'manobal/realtime:local'
        }
      ]
    }
  }
}

resource acuteApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${prefix}-acute'
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${engineIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: env.id
    template: {
      containers: [
        {
          name: 'acute'
          image: 'manobal/engine:local'
        }
      ]
    }
  }
}

resource frontDoor 'Microsoft.Cdn/profiles@2024-02-01' = {
  name: '${prefix}-afd'
  location: 'global'
  tags: tags
  sku: { name: 'Standard_AzureFrontDoor' }
}

resource webPubSub 'Microsoft.SignalRService/webPubSub@2024-03-01' = {
  name: '${prefix}-pubsub'
  location: location
  tags: tags
  sku: { name: 'Free_F1', tier: 'Free', capacity: 1 }
  properties: {
    disableLocalAuth: true
  }
}

resource acs 'Microsoft.Communication/communicationServices@2023-04-01' = {
  name: '${prefix}-acs'
  location: 'global'
  tags: tags
  properties: {
    dataLocation: 'United States'
  }
}

resource speech 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: '${prefix}-speech'
  location: location
  tags: tags
  kind: 'SpeechServices'
  sku: { name: 'S0' }
  properties: { publicNetworkAccess: 'Enabled' }
}

resource translator 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: '${prefix}-translator'
  location: location
  tags: tags
  kind: 'TextTranslation'
  sku: { name: 'S1' }
  properties: { publicNetworkAccess: 'Enabled' }
}

resource contentSafety 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: '${prefix}-contentsafety'
  location: location
  tags: tags
  kind: 'ContentSafety'
  sku: { name: 'S0' }
  properties: { publicNetworkAccess: 'Enabled' }
}

resource foundry 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: '${prefix}-foundry'
  location: location
  tags: tags
  kind: 'OpenAI'
  sku: { name: 'S0' }
  properties: { publicNetworkAccess: 'Enabled' }
}

var deployments = [
  { name: 'main', model: 'gpt-4o' }
  { name: 'fast', model: 'gpt-4o-mini' }
  { name: 'open', model: 'Phi-4' }
  { name: 'embeddings', model: 'text-embedding-3-small' }
  { name: 'alt', model: 'grok-not-for-personnel' }
]

resource foundryDeployments 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = [for item in deployments: {
  parent: foundry
  name: item.name
  sku: { name: 'Standard', capacity: 1 }
  properties: {
    model: {
      format: 'OpenAI'
      name: item.model
      version: '1'
    }
  }
}]

resource budget 'Microsoft.Consumption/budgets@2023-05-01' = {
  name: '${prefix}-daily-cap'
  properties: {
    timeGrain: 'Monthly'
    amount: costCapInr
    category: 'Cost'
    timePeriod: {
      startDate: '2026-09-01'
      endDate: '2027-09-01'
    }
    notifications: {
      Actual_GreaterThan_80_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 80
        contactEmails: [
          'wdec-synthetic@example.invalid'
        ]
      }
    }
  }
}

output engineFqdn string = engineApp.properties.configuration.ingress.fqdn
output webFqdn string = webApp.properties.configuration.ingress.fqdn
output keyVaultUri string = keyVault.properties.vaultUri
output appInsightsConnection string = appInsights.properties.ConnectionString
output webHostHint string = webHost
output githubIdentityId string = githubIdentity.id
