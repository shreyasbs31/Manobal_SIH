targetScope = 'resourceGroup'

@description('Azure region for the application and data plane.')
param location string = resourceGroup().location

@description('Short azd environment name, such as stage or demo.')
@minLength(2)
param environmentName string

@description('Resource name prefix.')
@minLength(2)
param prefix string = 'manobal'

@description('Create only shared infrastructure before images and secrets exist.')
param bootstrapMode bool = true

@description('Immutable image tag built in Azure Container Registry.')
param imageTag string = 'bootstrap'

@description('Enable the Front Door route only after verification succeeds.')
param publicEndpointEnabled bool = false

@description('Object ID of the person running the first deployment.')
param deployerPrincipalId string = ''

@allowed([
  'User'
  'ServicePrincipal'
])
param deployerPrincipalType string = 'User'

@description('Email address for cost and availability notifications.')
param alertEmail string = ''

@minValue(1)
param monthlyBudgetAmount int = 100000

@description('Resource group containing the existing AI resources.')
param existingAiResourceGroup string = 'rg-manobal-ai'

param foundryName string = 'manobal-ai-resource'
param foundryProjectName string = 'manobal-ai'
param speechName string = 'manobal-speech'
param translatorName string = 'manobal-translator'
param contentSafetyName string = 'manobal-safety'
param acsName string = 'manobal-acs'

param aiDeploymentMain string = 'gpt-5.6-sol'
param aiDeploymentFast string = 'fast'
param aiDeploymentOpen string = 'open_'
param aiDeploymentEmbed string = 'embed'
param aiDeploymentEmbedMl string = 'embed-m1'
param aiDeploymentRerank string = 'Cohere-rerank-v4.0-fast'
param aiDeploymentJudge string = 'judge'
param aiDeploymentImage string = 'image'
param aiDeploymentSttFallback string = 'stt_fallback'
param aiDeploymentAlt string = 'alt'

@allowed([
  'Detection'
  'Prevention'
])
param wafMode string = 'Detection'

param postgresSkuName string = 'Standard_D2ds_v5'
param postgresStorageGb int = 128
param postgresBackupDays int = 14

@description('Budget period start. Keep the first day of the current month.')
param budgetStartDate string = utcNow('yyyy-MM-01')

var stem = toLower('${prefix}-${environmentName}')
var uniqueSuffix = substring(uniqueString(subscription().id, resourceGroup().id), 0, 6)
var commonTags = {
  product: 'manobal'
  environment: environmentName
  syntheticDataOnly: 'true'
  'azd-env-name': environmentName
}

var vnetName = '${stem}-vnet'
var environmentResourceName = '${stem}-cae'
var registryName = take(replace('${stem}acr${uniqueSuffix}', '-', ''), 50)
var appVaultName = take(replace('${stem}-app-kv-${uniqueSuffix}', '-', ''), 24)
var identityVaultName = take(replace('${stem}-vault-kv-${uniqueSuffix}', '-', ''), 24)
var storageName = take(replace('${stem}data${uniqueSuffix}', '-', ''), 24)
var redisName = take('${stem}-redis-${uniqueSuffix}', 60)
var coreDbName = take('${stem}-core-pg-${uniqueSuffix}', 63)
var vaultDbName = take('${stem}-vault-pg-${uniqueSuffix}', 63)
var gatewayName = '${stem}-gateway'
var webName = '${stem}-web'
var engineName = '${stem}-engine'
var acuteName = '${stem}-acute'
var vaultName = '${stem}-vault'
var realtimeName = '${stem}-realtime'
var coreMigrateJobName = '${stem}-core-migrate'
var vaultMigrateJobName = '${stem}-vault-migrate'
var seedJobName = '${stem}-seed'
var frontDoorProfileName = '${stem}-afd'
var frontDoorEndpointName = take('${stem}-${uniqueSuffix}', 46)
var wafPolicyName = take(replace('${stem}waf', '-', ''), 128)

var placeholderSecretNames = {
  accessJwt: 'access-jwt'
  realtimeJwt: 'realtime-jwt'
  incidentHmac: 'incident-hmac'
  grantPrivatePem: 'grant-private-pem'
  judgeAccessHash: 'judge-access-hash'
  operatorAccessHash: 'operator-access-hash'
  demoGateJwt: 'demo-gate-jwt'
  deepgramApiKey: 'deepgram-api-key'
  speechKey: 'speech-key'
  translatorKey: 'translator-key'
  contentSafetyKey: 'content-safety-key'
  acsConnectionString: 'acs-connection-string'
  grantPublicPem: 'grant-public-pem'
  tokenHmac: 'vault-token-hmac'
  tokeniseIngest: 'tokenise-ingest'
}

var acrTasksRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  'fb382eab-e894-4461-af04-94435c366c3f'
)
var keyVaultSecretsOfficerRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  'b86a8fe4-44ce-4948-aee5-eccb2c155cd7'
)
var keyVaultSecretsUserRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '4633458b-17de-408a-b874-0445c86b69e6'
)
var keyVaultCryptoUserRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '12338af0-0e69-4776-bea7-57ae8d297424'
)
var keyVaultCryptoOfficerRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '14b46e9e-c2b7-41b4-b07b-48a6ebf60603'
)
var blobContributorRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
)
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${stem}-logs'
  location: location
  tags: commonTags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${stem}-insights'
  location: location
  tags: commonTags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

resource gatewayIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${stem}-id-gateway'
  location: location
  tags: commonTags
}

resource webIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${stem}-id-web'
  location: location
  tags: commonTags
}

resource engineIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${stem}-id-engine'
  location: location
  tags: commonTags
}

resource vaultIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${stem}-id-vault'
  location: location
  tags: commonTags
}

resource realtimeIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${stem}-id-realtime'
  location: location
  tags: commonTags
}

resource coreMigrationIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${stem}-id-core-migrate'
  location: location
  tags: commonTags
}

resource vaultMigrationIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${stem}-id-vault-migrate'
  location: location
  tags: commonTags
}

resource registry 'Microsoft.ContainerRegistry/registries@2025-04-01' = {
  #disable-next-line BCP334
  name: registryName
  location: location
  tags: commonTags
  sku: {
    name: 'Premium'
  }
  properties: {
    adminUserEnabled: false
    anonymousPullEnabled: false
    publicNetworkAccess: 'Enabled'
    policies: {
      exportPolicy: {
        status: 'enabled'
      }
      quarantinePolicy: {
        status: 'disabled'
      }
      retentionPolicy: {
        days: 30
        status: 'enabled'
      }
      trustPolicy: {
        status: 'disabled'
        type: 'Notary'
      }
    }
  }
}

module acrPullAssignments './acr-pull-roles.bicep' = {
  name: 'acr-pull-roles'
  params: {
    registryName: registry.name
    principalIds: [
      gatewayIdentity.properties.principalId
      webIdentity.properties.principalId
      engineIdentity.properties.principalId
      vaultIdentity.properties.principalId
      realtimeIdentity.properties.principalId
      coreMigrationIdentity.properties.principalId
      vaultMigrationIdentity.properties.principalId
    ]
  }
}

resource deployerAcrTasks 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployerPrincipalId)) {
  name: guid(registry.id, deployerPrincipalId, 'acr-tasks')
  scope: registry
  properties: {
    principalId: deployerPrincipalId
    principalType: deployerPrincipalType
    roleDefinitionId: acrTasksRoleId
  }
}

resource appVault 'Microsoft.KeyVault/vaults@2024-11-01' = {
  name: appVaultName
  location: location
  tags: commonTags
  properties: {
    tenantId: tenant().tenantId
    enableRbacAuthorization: true
    enablePurgeProtection: true
    enableSoftDelete: true
    publicNetworkAccess: 'Enabled'
    softDeleteRetentionInDays: 90
    sku: {
      family: 'A'
      name: 'standard'
    }
  }
}

resource identityVault 'Microsoft.KeyVault/vaults@2024-11-01' = {
  name: identityVaultName
  location: location
  tags: commonTags
  properties: {
    tenantId: tenant().tenantId
    enableRbacAuthorization: true
    enablePurgeProtection: true
    enableSoftDelete: true
    publicNetworkAccess: 'Enabled'
    softDeleteRetentionInDays: 90
    sku: {
      family: 'A'
      name: 'premium'
    }
  }
}

resource deployerAppSecrets 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployerPrincipalId)) {
  name: guid(appVault.id, deployerPrincipalId, 'secrets-officer')
  scope: appVault
  properties: {
    principalId: deployerPrincipalId
    principalType: deployerPrincipalType
    roleDefinitionId: keyVaultSecretsOfficerRoleId
  }
}

resource deployerVaultSecrets 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployerPrincipalId)) {
  name: guid(identityVault.id, deployerPrincipalId, 'secrets-officer')
  scope: identityVault
  properties: {
    principalId: deployerPrincipalId
    principalType: deployerPrincipalType
    roleDefinitionId: keyVaultSecretsOfficerRoleId
  }
}

resource deployerVaultCrypto 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployerPrincipalId)) {
  name: guid(identityVault.id, deployerPrincipalId, 'crypto-officer')
  scope: identityVault
  properties: {
    principalId: deployerPrincipalId
    principalType: deployerPrincipalType
    roleDefinitionId: keyVaultCryptoOfficerRoleId
  }
}

resource engineAppSecrets 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(appVault.id, engineIdentity.id, 'secrets-user')
  scope: appVault
  properties: {
    principalId: engineIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: keyVaultSecretsUserRoleId
  }
}

resource realtimeAppSecrets 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(appVault.id, realtimeIdentity.id, 'secrets-user')
  scope: appVault
  properties: {
    principalId: realtimeIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: keyVaultSecretsUserRoleId
  }
}

resource vaultSecrets 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(identityVault.id, vaultIdentity.id, 'secrets-user')
  scope: identityVault
  properties: {
    principalId: vaultIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: keyVaultSecretsUserRoleId
  }
}

resource vaultCrypto 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(identityVault.id, vaultIdentity.id, 'crypto-user')
  scope: identityVault
  properties: {
    principalId: vaultIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: keyVaultCryptoUserRoleId
  }
}

resource seedVaultSecrets 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(identityVault.id, coreMigrationIdentity.id, 'seed-secrets-user')
  scope: identityVault
  properties: {
    principalId: coreMigrationIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: keyVaultSecretsUserRoleId
  }
}

resource vaultKek 'Microsoft.KeyVault/vaults/keys@2024-11-01' = if (!bootstrapMode) {
  parent: identityVault
  name: 'vault-kek'
  properties: {
    attributes: {
      enabled: true
      exportable: false
    }
    keyOps: [
      'wrapKey'
      'unwrapKey'
    ]
    kty: 'RSA-HSM'
    keySize: 3072
  }
  dependsOn: [
    deployerVaultCrypto
  ]
}

resource storage 'Microsoft.Storage/storageAccounts@2025-01-01' = {
  #disable-next-line BCP334
  name: storageName
  location: location
  tags: commonTags
  sku: {
    name: 'Standard_ZRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    allowCrossTenantReplication: false
    defaultToOAuthAuthentication: true
    isHnsEnabled: false
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Enabled'
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2025-01-01' = {
  parent: storage
  name: 'default'
  properties: {
    containerDeleteRetentionPolicy: {
      enabled: true
      days: 14
    }
    deleteRetentionPolicy: {
      enabled: true
      days: 14
      allowPermanentDelete: false
    }
    isVersioningEnabled: true
  }
}

resource auditContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-01-01' = {
  parent: blobService
  name: 'audit-anchors'
  properties: {
    publicAccess: 'None'
  }
}

resource audioContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-01-01' = {
  parent: blobService
  name: 'audio'
  properties: {
    publicAccess: 'None'
  }
}

resource engineBlobRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, engineIdentity.id, 'blob-contributor')
  scope: storage
  properties: {
    principalId: engineIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: blobContributorRoleId
  }
}

resource vnet 'Microsoft.Network/virtualNetworks@2024-07-01' = {
  name: vnetName
  location: location
  tags: commonTags
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.42.0.0/16'
      ]
    }
  }
}

resource containerAppsSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-07-01' = {
  parent: vnet
  name: 'container-apps'
  properties: {
    addressPrefix: '10.42.0.0/23'
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

resource coreDbSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-07-01' = {
  parent: vnet
  name: 'core-postgres'
  properties: {
    addressPrefix: '10.42.4.0/24'
    delegations: [
      {
        name: 'postgres-delegation'
        properties: {
          serviceName: 'Microsoft.DBforPostgreSQL/flexibleServers'
        }
      }
    ]
  }
}

resource vaultDbSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-07-01' = {
  parent: vnet
  name: 'vault-postgres'
  properties: {
    addressPrefix: '10.42.5.0/24'
    delegations: [
      {
        name: 'postgres-delegation'
        properties: {
          serviceName: 'Microsoft.DBforPostgreSQL/flexibleServers'
        }
      }
    ]
  }
}

resource privateEndpointSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-07-01' = {
  parent: vnet
  name: 'private-endpoints'
  properties: {
    addressPrefix: '10.42.6.0/24'
    privateEndpointNetworkPolicies: 'Disabled'
  }
}

resource postgresDns 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: '${stem}.private.postgres.database.azure.com'
  location: 'global'
  tags: commonTags
}

resource postgresDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: postgresDns
  name: '${stem}-postgres-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}

resource coreDb 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: coreDbName
  location: location
  tags: commonTags
  sku: {
    name: postgresSkuName
    tier: 'GeneralPurpose'
  }
  properties: {
    authConfig: {
      activeDirectoryAuth: 'Enabled'
      passwordAuth: 'Disabled'
      tenantId: tenant().tenantId
    }
    backup: {
      backupRetentionDays: postgresBackupDays
      geoRedundantBackup: 'Disabled'
    }
    createMode: 'Default'
    highAvailability: {
      mode: 'Disabled'
    }
    network: {
      delegatedSubnetResourceId: coreDbSubnet.id
      privateDnsZoneArmResourceId: postgresDns.id
    }
    storage: {
      autoGrow: 'Enabled'
      storageSizeGB: postgresStorageGb
    }
    version: '16'
  }
  dependsOn: [
    postgresDnsLink
  ]
}

resource coreDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: coreDb
  name: 'manobal_core'
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

module coreDbAdmin './postgres-admin.bicep' = {
  name: 'core-postgres-admin'
  params: {
    serverName: coreDb.name
    principalId: coreMigrationIdentity.properties.principalId
    principalName: coreMigrationIdentity.name
    tenantId: tenant().tenantId
  }
}

resource coreExtensions 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2024-08-01' = {
  parent: coreDb
  name: 'azure.extensions'
  properties: {
    source: 'user-override'
    value: 'TIMESCALEDB,vector,ltree,pgcrypto,uuid-ossp'
  }
}

resource corePreload 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2024-08-01' = {
  parent: coreDb
  name: 'shared_preload_libraries'
  properties: {
    source: 'user-override'
    value: 'timescaledb'
  }
}

resource vaultDb 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: vaultDbName
  location: location
  tags: commonTags
  sku: {
    name: postgresSkuName
    tier: 'GeneralPurpose'
  }
  properties: {
    authConfig: {
      activeDirectoryAuth: 'Enabled'
      passwordAuth: 'Disabled'
      tenantId: tenant().tenantId
    }
    backup: {
      backupRetentionDays: postgresBackupDays
      geoRedundantBackup: 'Disabled'
    }
    createMode: 'Default'
    highAvailability: {
      mode: 'Disabled'
    }
    network: {
      delegatedSubnetResourceId: vaultDbSubnet.id
      privateDnsZoneArmResourceId: postgresDns.id
    }
    storage: {
      autoGrow: 'Enabled'
      storageSizeGB: postgresStorageGb
    }
    version: '16'
  }
  dependsOn: [
    postgresDnsLink
  ]
}

resource vaultDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: vaultDb
  name: 'manobal_vault'
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

module vaultDbAdmin './postgres-admin.bicep' = {
  name: 'vault-postgres-admin'
  params: {
    serverName: vaultDb.name
    principalId: vaultMigrationIdentity.properties.principalId
    principalName: vaultMigrationIdentity.name
    tenantId: tenant().tenantId
  }
}

resource vaultExtensions 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2024-08-01' = {
  parent: vaultDb
  name: 'azure.extensions'
  properties: {
    source: 'user-override'
    value: 'pgcrypto'
  }
}

resource redis 'Microsoft.Cache/redisEnterprise@2025-07-01' = {
  name: redisName
  location: location
  tags: commonTags
  sku: {
    name: 'Balanced_B0'
  }
  properties: {
    highAvailability: 'Enabled'
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
  }
}

resource redisDatabase 'Microsoft.Cache/redisEnterprise/databases@2025-07-01' = {
  parent: redis
  name: 'default'
  properties: {
    accessKeysAuthentication: 'Enabled'
    clientProtocol: 'Encrypted'
    clusteringPolicy: 'NoCluster'
    evictionPolicy: 'NoEviction'
    persistence: {
      aofEnabled: false
      rdbEnabled: false
    }
    port: 10000
  }
}

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2025-07-01' = {
  name: environmentResourceName
  location: location
  tags: commonTags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
    publicNetworkAccess: 'Disabled'
    vnetConfiguration: {
      infrastructureSubnetId: containerAppsSubnet.id
      internal: true
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
    zoneRedundant: false
  }
}

module engineAiRoles './ai-role-assignments.bicep' = {
  scope: resourceGroup(existingAiResourceGroup)
  name: 'engine-ai-roles'
  params: {
    foundryName: foundryName
    speechName: speechName
    translatorName: translatorName
    contentSafetyName: contentSafetyName
    principalId: engineIdentity.properties.principalId
  }
}

var gatewayImage = '${registry.properties.loginServer}/manobal/gateway:${imageTag}'
var webImage = '${registry.properties.loginServer}/manobal/web:${imageTag}'
var engineImage = '${registry.properties.loginServer}/manobal/engine:${imageTag}'
var vaultImage = '${registry.properties.loginServer}/manobal/vault:${imageTag}'
var realtimeImage = '${registry.properties.loginServer}/manobal/realtime:${imageTag}'
var synthImage = '${registry.properties.loginServer}/manobal/synth:${imageTag}'
var foundryEndpoint = 'https://${foundryName}.services.ai.azure.com/api/projects/${foundryProjectName}'
var speechEndpoint = 'https://${location}.api.cognitive.microsoft.com'
var translatorEndpoint = 'https://api.cognitive.microsofttranslator.com'
var contentSafetyEndpoint = 'https://${contentSafetyName}.cognitiveservices.azure.com'
var acsEndpoint = 'https://${acsName}.communication.azure.com'
var redisUrl = 'rediss://:${uriComponent(redisDatabase.listKeys().primaryKey)}@${redisName}.${location}.redis.azure.net:10000/0'
var coreAsyncUrl = 'postgresql+asyncpg://${engineIdentity.name}@${coreDb.properties.fullyQualifiedDomainName}/manobal_core?sslmode=require'
var vaultAsyncUrl = 'postgresql+asyncpg://${vaultIdentity.name}@${vaultDb.properties.fullyQualifiedDomainName}/manobal_vault?sslmode=require'
var coreMigrationPostgresUrl = 'postgresql+psycopg://${coreMigrationIdentity.name}@${coreDb.properties.fullyQualifiedDomainName}/postgres?sslmode=require'
var coreMigrationAppUrl = 'postgresql+psycopg://${coreMigrationIdentity.name}@${coreDb.properties.fullyQualifiedDomainName}/manobal_core?sslmode=require'
var vaultMigrationPostgresUrl = 'postgresql+psycopg://${vaultMigrationIdentity.name}@${vaultDb.properties.fullyQualifiedDomainName}/postgres?sslmode=require'
var vaultMigrationAppUrl = 'postgresql+psycopg://${vaultMigrationIdentity.name}@${vaultDb.properties.fullyQualifiedDomainName}/manobal_vault?sslmode=require'

resource gatewayApp 'Microsoft.App/containerApps@2025-07-01' = if (!bootstrapMode) {
  name: gatewayName
  location: location
  tags: union(commonTags, {
    'azd-service-name': 'gateway'
  })
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${gatewayIdentity.id}': {}
    }
  }
  properties: {
    environmentId: containerAppsEnvironment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        allowInsecure: false
        external: true
        targetPort: 8080
        transport: 'http'
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      registries: [
        {
          identity: gatewayIdentity.id
          server: registry.properties.loginServer
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'gateway'
          image: gatewayImage
          env: [
            {
              name: 'WEB_APP_NAME'
              value: webName
            }
            {
              name: 'ENGINE_APP_NAME'
              value: engineName
            }
            {
              name: 'REALTIME_APP_NAME'
              value: realtimeName
            }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/healthz'
                port: 8080
                scheme: 'HTTP'
              }
              initialDelaySeconds: 5
              periodSeconds: 10
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/healthz'
                port: 8080
                scheme: 'HTTP'
              }
              initialDelaySeconds: 2
              periodSeconds: 5
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        maxReplicas: 1
        minReplicas: 1
      }
    }
  }
  dependsOn: [
    acrPullAssignments
  ]
}

resource webApp 'Microsoft.App/containerApps@2025-07-01' = if (!bootstrapMode) {
  name: webName
  location: location
  tags: union(commonTags, {
    'azd-service-name': 'web'
  })
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${webIdentity.id}': {}
    }
  }
  properties: {
    environmentId: containerAppsEnvironment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        allowInsecure: false
        external: false
        targetPort: 3000
        transport: 'http'
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      registries: [
        {
          identity: webIdentity.id
          server: registry.properties.loginServer
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'web'
          image: webImage
          env: [
            {
              name: 'NEXT_PUBLIC_MANOBAL_MODE'
              value: 'demo'
            }
            {
              name: 'DEMO_GATE_REQUIRED'
              value: 'true'
            }
            {
              name: 'ENGINE_INTERNAL_URL'
              value: 'http://${engineName}:8000'
            }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/api/health'
                port: 3000
                scheme: 'HTTP'
              }
              initialDelaySeconds: 10
              periodSeconds: 15
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/api/health'
                port: 3000
                scheme: 'HTTP'
              }
              initialDelaySeconds: 5
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
        maxReplicas: 1
        minReplicas: 1
      }
    }
  }
  dependsOn: [
    acrPullAssignments
  ]
}

resource realtimeApp 'Microsoft.App/containerApps@2025-07-01' = if (!bootstrapMode) {
  name: realtimeName
  location: location
  tags: union(commonTags, {
    'azd-service-name': 'realtime'
  })
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${realtimeIdentity.id}': {}
    }
  }
  properties: {
    environmentId: containerAppsEnvironment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        allowInsecure: false
        external: false
        targetPort: 8080
        transport: 'http'
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      registries: [
        {
          identity: realtimeIdentity.id
          server: registry.properties.loginServer
        }
      ]
      secrets: [
        {
          name: 'realtime-jwt'
          keyVaultUrl: '${appVault.properties.vaultUri}secrets/${placeholderSecretNames.realtimeJwt}'
          identity: realtimeIdentity.id
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'realtime'
          image: realtimeImage
          env: [
            {
              name: 'PORT'
              value: '8080'
            }
            {
              name: 'JWT_SECRET'
              secretRef: 'realtime-jwt'
            }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8080
                scheme: 'HTTP'
              }
              initialDelaySeconds: 5
              periodSeconds: 10
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: 8080
                scheme: 'HTTP'
              }
              initialDelaySeconds: 2
              periodSeconds: 5
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        maxReplicas: 1
        minReplicas: 1
      }
    }
  }
  dependsOn: [
    acrPullAssignments
    realtimeAppSecrets
  ]
}

resource vaultApp 'Microsoft.App/containerApps@2025-07-01' = if (!bootstrapMode) {
  name: vaultName
  location: location
  tags: union(commonTags, {
    'azd-service-name': 'vault'
  })
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${vaultIdentity.id}': {}
    }
  }
  properties: {
    environmentId: containerAppsEnvironment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        allowInsecure: false
        external: false
        targetPort: 8100
        transport: 'http'
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      registries: [
        {
          identity: vaultIdentity.id
          server: registry.properties.loginServer
        }
      ]
      secrets: [
        {
          name: 'grant-public-pem'
          keyVaultUrl: '${identityVault.properties.vaultUri}secrets/${placeholderSecretNames.grantPublicPem}'
          identity: vaultIdentity.id
        }
        {
          name: 'tokenise-ingest'
          keyVaultUrl: '${identityVault.properties.vaultUri}secrets/${placeholderSecretNames.tokeniseIngest}'
          identity: vaultIdentity.id
        }
        {
          name: 'redis-url'
          value: redisUrl
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'vault'
          image: vaultImage
          env: [
            {
              name: 'MANOBAL_MODE'
              value: 'demo'
            }
            {
              name: 'MANOBAL_SKIP_SECRETS'
              value: '1'
            }
            {
              name: 'AZURE_CLIENT_ID'
              value: vaultIdentity.properties.clientId
            }
            {
              name: 'AZURE_TOKEN_CREDENTIALS'
              value: 'ManagedIdentityCredential'
            }
            {
              name: 'VAULT_DATABASE_URL'
              value: vaultAsyncUrl
            }
            {
              name: 'VAULT_DATABASE_ENTRA_AUTH'
              value: '1'
            }
            {
              name: 'REDIS_URL'
              secretRef: 'redis-url'
            }
            {
              name: 'KEY_PROVIDER'
              value: 'azure'
            }
            {
              name: 'KEYVAULT_URI'
              value: identityVault.properties.vaultUri
            }
            {
              name: 'KV_KEK_NAME'
              value: 'vault-kek'
            }
            {
              name: 'KV_TOKEN_KEY_NAME'
              value: placeholderSecretNames.tokenHmac
            }
            {
              name: 'GRANT_PUBLIC_KEY_PEM'
              secretRef: 'grant-public-pem'
            }
            {
              name: 'TOKENISE_INGEST_SECRET'
              secretRef: 'tokenise-ingest'
            }
          ]
          probes: [
            {
              type: 'Liveness'
              tcpSocket: {
                port: 8100
              }
              initialDelaySeconds: 20
              periodSeconds: 15
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: 8100
                scheme: 'HTTP'
              }
              failureThreshold: 30
              initialDelaySeconds: 60
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
        maxReplicas: 1
        minReplicas: 1
      }
    }
  }
  dependsOn: [
    acrPullAssignments
    vaultSecrets
    vaultCrypto
    vaultKek
  ]
}

resource frontDoorProfile 'Microsoft.Cdn/profiles@2025-04-15' = if (!bootstrapMode) {
  name: frontDoorProfileName
  location: 'global'
  tags: commonTags
  sku: {
    name: 'Premium_AzureFrontDoor'
  }
}

resource frontDoorEndpoint 'Microsoft.Cdn/profiles/afdEndpoints@2025-04-15' = if (!bootstrapMode) {
  parent: frontDoorProfile
  name: frontDoorEndpointName
  location: 'global'
  tags: commonTags
  properties: {
    enabledState: 'Enabled'
  }
}

resource engineApp 'Microsoft.App/containerApps@2025-07-01' = if (!bootstrapMode) {
  name: engineName
  location: location
  tags: union(commonTags, {
    'azd-service-name': 'engine'
  })
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${engineIdentity.id}': {}
    }
  }
  properties: {
    environmentId: containerAppsEnvironment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        allowInsecure: false
        external: false
        targetPort: 8000
        transport: 'http'
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      registries: [
        {
          identity: engineIdentity.id
          server: registry.properties.loginServer
        }
      ]
      secrets: [
        {
          name: 'access-jwt'
          keyVaultUrl: '${appVault.properties.vaultUri}secrets/${placeholderSecretNames.accessJwt}'
          identity: engineIdentity.id
        }
        {
          name: 'realtime-jwt'
          keyVaultUrl: '${appVault.properties.vaultUri}secrets/${placeholderSecretNames.realtimeJwt}'
          identity: engineIdentity.id
        }
        {
          name: 'incident-hmac'
          keyVaultUrl: '${appVault.properties.vaultUri}secrets/${placeholderSecretNames.incidentHmac}'
          identity: engineIdentity.id
        }
        {
          name: 'grant-private-pem'
          keyVaultUrl: '${appVault.properties.vaultUri}secrets/${placeholderSecretNames.grantPrivatePem}'
          identity: engineIdentity.id
        }
        {
          name: 'judge-access-hash'
          keyVaultUrl: '${appVault.properties.vaultUri}secrets/${placeholderSecretNames.judgeAccessHash}'
          identity: engineIdentity.id
        }
        {
          name: 'operator-access-hash'
          keyVaultUrl: '${appVault.properties.vaultUri}secrets/${placeholderSecretNames.operatorAccessHash}'
          identity: engineIdentity.id
        }
        {
          name: 'demo-gate-jwt'
          keyVaultUrl: '${appVault.properties.vaultUri}secrets/${placeholderSecretNames.demoGateJwt}'
          identity: engineIdentity.id
        }
        {
          name: 'deepgram-api-key'
          keyVaultUrl: '${appVault.properties.vaultUri}secrets/${placeholderSecretNames.deepgramApiKey}'
          identity: engineIdentity.id
        }
        {
          name: 'speech-key'
          keyVaultUrl: '${appVault.properties.vaultUri}secrets/${placeholderSecretNames.speechKey}'
          identity: engineIdentity.id
        }
        {
          name: 'translator-key'
          keyVaultUrl: '${appVault.properties.vaultUri}secrets/${placeholderSecretNames.translatorKey}'
          identity: engineIdentity.id
        }
        {
          name: 'content-safety-key'
          keyVaultUrl: '${appVault.properties.vaultUri}secrets/${placeholderSecretNames.contentSafetyKey}'
          identity: engineIdentity.id
        }
        {
          name: 'acs-connection-string'
          keyVaultUrl: '${appVault.properties.vaultUri}secrets/${placeholderSecretNames.acsConnectionString}'
          identity: engineIdentity.id
        }
        {
          name: 'redis-url'
          value: redisUrl
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'engine'
          image: engineImage
          env: [
            {
              name: 'MANOBAL_MODE'
              value: 'demo'
            }
            {
              name: 'MANOBAL_SKIP_SECRETS'
              value: '1'
            }
            {
              name: 'MANOBAL_REQUIRE_LIVE_PROVIDERS'
              value: '1'
            }
            {
              name: 'WEB_ORIGIN'
              value: 'https://${frontDoorEndpoint!.properties.hostName}'
            }
            {
              name: 'AZURE_CLIENT_ID'
              value: engineIdentity.properties.clientId
            }
            {
              name: 'AZURE_TOKEN_CREDENTIALS'
              value: 'ManagedIdentityCredential'
            }
            {
              name: 'CORE_DATABASE_URL'
              value: coreAsyncUrl
            }
            {
              name: 'CORE_DATABASE_ENTRA_AUTH'
              value: '1'
            }
            {
              name: 'REDIS_URL'
              secretRef: 'redis-url'
            }
            {
              name: 'VAULT_API_URL'
              value: 'http://${vaultName}:8100'
            }
            {
              name: 'REALTIME_URL'
              value: 'ws://${realtimeName}:8080'
            }
            {
              name: 'ACCESS_JWT_SECRET'
              secretRef: 'access-jwt'
            }
            {
              name: 'ACCESS_TOKEN_MINUTES'
              value: '480'
            }
            {
              name: 'REALTIME_JWT_SECRET'
              secretRef: 'realtime-jwt'
            }
            {
              name: 'INCIDENT_HMAC_SECRET'
              secretRef: 'incident-hmac'
            }
            {
              name: 'GRANT_PRIVATE_KEY_PEM'
              secretRef: 'grant-private-pem'
            }
            {
              name: 'DEMO_GATE_REQUIRED'
              value: '1'
            }
            {
              name: 'DEMO_GATE_ACCESS_HASH'
              secretRef: 'judge-access-hash'
            }
            {
              name: 'DEMO_GATE_OPERATOR_HASH'
              secretRef: 'operator-access-hash'
            }
            {
              name: 'DEMO_GATE_JWT_SECRET'
              secretRef: 'demo-gate-jwt'
            }
            {
              name: 'DEMO_GATE_COOKIE_SECURE'
              value: '1'
            }
            {
              name: 'FORCE_HSTS'
              value: '1'
            }
            {
              name: 'BLOB_ENDPOINT'
              value: 'https://${storage.name}.blob.${environment().suffixes.storage}'
            }
            {
              name: 'BLOB_ACCOUNT_NAME'
              value: storage.name
            }
            {
              name: 'BLOB_CONTAINER'
              value: auditContainer.name
            }
            {
              name: 'BLOB_USE_MANAGED_IDENTITY'
              value: '1'
            }
            {
              name: 'FOUNDRY_ENDPOINT'
              value: foundryEndpoint
            }
            {
              name: 'AI_DEPLOYMENT_MAIN'
              value: aiDeploymentMain
            }
            {
              name: 'AI_DEPLOYMENT_FAST'
              value: aiDeploymentFast
            }
            {
              name: 'AI_DEPLOYMENT_OPEN'
              value: aiDeploymentOpen
            }
            {
              name: 'AI_DEPLOYMENT_EMBED'
              value: aiDeploymentEmbed
            }
            {
              name: 'AI_DEPLOYMENT_EMBED_ML'
              value: aiDeploymentEmbedMl
            }
            {
              name: 'AI_DEPLOYMENT_RERANK'
              value: aiDeploymentRerank
            }
            {
              name: 'AI_DEPLOYMENT_JUDGE'
              value: aiDeploymentJudge
            }
            {
              name: 'AI_DEPLOYMENT_IMAGE'
              value: aiDeploymentImage
            }
            {
              name: 'AI_DEPLOYMENT_STT_FALLBACK'
              value: aiDeploymentSttFallback
            }
            {
              name: 'AI_DEPLOYMENT_ALT'
              value: aiDeploymentAlt
            }
            {
              name: 'DEEPGRAM_API_KEY'
              secretRef: 'deepgram-api-key'
            }
            {
              name: 'DG_STT_MODEL_EN'
              value: 'nova-3'
            }
            {
              name: 'DG_STT_MODEL_HI'
              value: 'nova-3'
            }
            {
              name: 'DG_TTS_VOICE_EN'
              value: 'aura-2-thalia-en'
            }
            {
              name: 'SPEECH_REGION'
              value: location
            }
            {
              name: 'SPEECH_ENDPOINT'
              value: speechEndpoint
            }
            {
              name: 'SPEECH_KEY'
              secretRef: 'speech-key'
            }
            {
              name: 'TRANSLATOR_ENDPOINT'
              value: translatorEndpoint
            }
            {
              name: 'TRANSLATOR_REGION'
              value: location
            }
            {
              name: 'TRANSLATOR_KEY'
              secretRef: 'translator-key'
            }
            {
              name: 'CONTENT_SAFETY_ENDPOINT'
              value: contentSafetyEndpoint
            }
            {
              name: 'CONTENT_SAFETY_KEY'
              secretRef: 'content-safety-key'
            }
            {
              name: 'ACS_ENDPOINT'
              value: acsEndpoint
            }
            {
              name: 'ACS_CONNECTION_STRING'
              secretRef: 'acs-connection-string'
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: appInsights.properties.ConnectionString
            }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/'
                port: 8000
                scheme: 'HTTP'
              }
              initialDelaySeconds: 20
              periodSeconds: 15
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/api/v1/system/health'
                port: 8000
                scheme: 'HTTP'
              }
              failureThreshold: 30
              initialDelaySeconds: 60
              periodSeconds: 10
            }
          ]
          resources: {
            cpu: json('2.0')
            memory: '4Gi'
          }
        }
      ]
      scale: {
        maxReplicas: 1
        minReplicas: 1
      }
    }
  }
  dependsOn: [
    acrPullAssignments
    engineAppSecrets
    engineBlobRole
    engineAiRoles
  ]
}

resource acuteApp 'Microsoft.App/containerApps@2025-07-01' = if (!bootstrapMode) {
  name: acuteName
  location: location
  tags: union(commonTags, {
    'azd-service-name': 'acute'
  })
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${engineIdentity.id}': {}
    }
  }
  properties: {
    environmentId: containerAppsEnvironment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      registries: [
        {
          identity: engineIdentity.id
          server: registry.properties.loginServer
        }
      ]
      secrets: [
        {
          name: 'access-jwt'
          keyVaultUrl: '${appVault.properties.vaultUri}secrets/${placeholderSecretNames.accessJwt}'
          identity: engineIdentity.id
        }
        {
          name: 'realtime-jwt'
          keyVaultUrl: '${appVault.properties.vaultUri}secrets/${placeholderSecretNames.realtimeJwt}'
          identity: engineIdentity.id
        }
        {
          name: 'incident-hmac'
          keyVaultUrl: '${appVault.properties.vaultUri}secrets/${placeholderSecretNames.incidentHmac}'
          identity: engineIdentity.id
        }
        {
          name: 'grant-private-pem'
          keyVaultUrl: '${appVault.properties.vaultUri}secrets/${placeholderSecretNames.grantPrivatePem}'
          identity: engineIdentity.id
        }
        {
          name: 'redis-url'
          value: redisUrl
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'acute'
          image: engineImage
          command: [
            'python'
            '-m'
            'app.acute_worker'
          ]
          env: [
            {
              name: 'MANOBAL_MODE'
              value: 'demo'
            }
            {
              name: 'MANOBAL_SKIP_SECRETS'
              value: '1'
            }
            {
              name: 'AZURE_CLIENT_ID'
              value: engineIdentity.properties.clientId
            }
            {
              name: 'CORE_DATABASE_URL'
              value: coreAsyncUrl
            }
            {
              name: 'CORE_DATABASE_ENTRA_AUTH'
              value: '1'
            }
            {
              name: 'REDIS_URL'
              secretRef: 'redis-url'
            }
            {
              name: 'VAULT_API_URL'
              value: 'http://${vaultName}:8100'
            }
            {
              name: 'REALTIME_URL'
              value: 'ws://${realtimeName}:8080'
            }
            {
              name: 'ACCESS_JWT_SECRET'
              secretRef: 'access-jwt'
            }
            {
              name: 'REALTIME_JWT_SECRET'
              secretRef: 'realtime-jwt'
            }
            {
              name: 'INCIDENT_HMAC_SECRET'
              secretRef: 'incident-hmac'
            }
            {
              name: 'GRANT_PRIVATE_KEY_PEM'
              secretRef: 'grant-private-pem'
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        maxReplicas: 1
        minReplicas: 1
      }
    }
  }
  dependsOn: [
    acrPullAssignments
    engineAppSecrets
  ]
}

resource coreMigrateJob 'Microsoft.App/jobs@2025-07-01' = if (!bootstrapMode) {
  name: coreMigrateJobName
  location: location
  tags: commonTags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${coreMigrationIdentity.id}': {}
    }
  }
  properties: {
    environmentId: containerAppsEnvironment.id
    workloadProfileName: 'Consumption'
    configuration: {
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
      registries: [
        {
          identity: coreMigrationIdentity.id
          server: registry.properties.loginServer
        }
      ]
      replicaRetryLimit: 1
      replicaTimeout: 1800
      triggerType: 'Manual'
    }
    template: {
      containers: [
        {
          name: 'core-migrate'
          image: engineImage
          command: [
            '/bin/sh'
            '-c'
          ]
          args: [
            'DATABASE_URL="$POSTGRES_DATABASE_URL" python -m app.db_bootstrap principal && CORE_DATABASE_URL="$APP_DATABASE_URL" CORE_DATABASE_ENTRA_AUTH=1 alembic -c services/engine/alembic.ini upgrade head && DATABASE_URL="$APP_DATABASE_URL" python -m app.db_bootstrap grants'
          ]
          env: [
            {
              name: 'MANOBAL_SKIP_SECRETS'
              value: '1'
            }
            {
              name: 'AZURE_CLIENT_ID'
              value: coreMigrationIdentity.properties.clientId
            }
            {
              name: 'POSTGRES_DATABASE_URL'
              value: coreMigrationPostgresUrl
            }
            {
              name: 'APP_DATABASE_URL'
              value: coreMigrationAppUrl
            }
            {
              name: 'APP_DATABASE_NAME'
              value: coreDatabase.name
            }
            {
              name: 'APP_IDENTITY_NAME'
              value: engineIdentity.name
            }
            {
              name: 'APP_IDENTITY_OBJECT_ID'
              value: engineIdentity.properties.principalId
            }
          ]
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
        }
      ]
    }
  }
  dependsOn: [
    acrPullAssignments
    coreDbAdmin
    coreExtensions
    corePreload
  ]
}

resource vaultMigrateJob 'Microsoft.App/jobs@2025-07-01' = if (!bootstrapMode) {
  name: vaultMigrateJobName
  location: location
  tags: commonTags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${vaultMigrationIdentity.id}': {}
    }
  }
  properties: {
    environmentId: containerAppsEnvironment.id
    workloadProfileName: 'Consumption'
    configuration: {
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
      registries: [
        {
          identity: vaultMigrationIdentity.id
          server: registry.properties.loginServer
        }
      ]
      replicaRetryLimit: 1
      replicaTimeout: 1800
      triggerType: 'Manual'
    }
    template: {
      containers: [
        {
          name: 'vault-migrate'
          image: vaultImage
          command: [
            '/bin/sh'
            '-c'
          ]
          args: [
            'DATABASE_URL="$POSTGRES_DATABASE_URL" python -m app.db_bootstrap principal && VAULT_DATABASE_URL="$APP_DATABASE_URL" VAULT_DATABASE_ENTRA_AUTH=1 alembic -c services/vault/alembic.ini upgrade head && DATABASE_URL="$APP_DATABASE_URL" python -m app.db_bootstrap grants'
          ]
          env: [
            {
              name: 'MANOBAL_SKIP_SECRETS'
              value: '1'
            }
            {
              name: 'AZURE_CLIENT_ID'
              value: vaultMigrationIdentity.properties.clientId
            }
            {
              name: 'POSTGRES_DATABASE_URL'
              value: vaultMigrationPostgresUrl
            }
            {
              name: 'APP_DATABASE_URL'
              value: vaultMigrationAppUrl
            }
            {
              name: 'APP_DATABASE_NAME'
              value: vaultDatabase.name
            }
            {
              name: 'APP_IDENTITY_NAME'
              value: vaultIdentity.name
            }
            {
              name: 'APP_IDENTITY_OBJECT_ID'
              value: vaultIdentity.properties.principalId
            }
          ]
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
        }
      ]
    }
  }
  dependsOn: [
    acrPullAssignments
    vaultDbAdmin
    vaultExtensions
  ]
}

resource seedJob 'Microsoft.App/jobs@2025-07-01' = if (!bootstrapMode) {
  name: seedJobName
  location: location
  tags: commonTags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${coreMigrationIdentity.id}': {}
    }
  }
  properties: {
    environmentId: containerAppsEnvironment.id
    workloadProfileName: 'Consumption'
    configuration: {
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
      registries: [
        {
          identity: coreMigrationIdentity.id
          server: registry.properties.loginServer
        }
      ]
      replicaRetryLimit: 0
      replicaTimeout: 3600
      secrets: [
        {
          name: 'tokenise-ingest'
          keyVaultUrl: '${identityVault.properties.vaultUri}secrets/${placeholderSecretNames.tokeniseIngest}'
          identity: coreMigrationIdentity.id
        }
      ]
      triggerType: 'Manual'
    }
    template: {
      containers: [
        {
          name: 'seed'
          image: synthImage
          command: [
            'python'
            '-m'
            'manobal_synth.cli'
          ]
          args: [
            'seed'
            '--personnel'
            '7200'
            '--days'
            '540'
            '--seed'
            '20260916'
          ]
          env: [
            {
              name: 'AZURE_CLIENT_ID'
              value: coreMigrationIdentity.properties.clientId
            }
            {
              name: 'CORE_DATABASE_ENTRA_AUTH'
              value: '1'
            }
            {
              name: 'CORE_ADMIN_DATABASE_URL'
              value: coreMigrationAppUrl
            }
            {
              name: 'VAULT_API_URL'
              value: 'http://${vaultName}:8100'
            }
            {
              name: 'TOKENISE_INGEST_SECRET'
              secretRef: 'tokenise-ingest'
            }
            {
              name: 'ENGINE_API_URL'
              value: 'http://${engineName}:8000'
            }
          ]
          resources: {
            cpu: json('2.0')
            memory: '4Gi'
          }
        }
      ]
    }
  }
  dependsOn: [
    acrPullAssignments
    seedVaultSecrets
  ]
}

resource frontDoorOriginGroup 'Microsoft.Cdn/profiles/originGroups@2025-04-15' = if (!bootstrapMode) {
  parent: frontDoorProfile
  name: 'gateway-origins'
  properties: {
    healthProbeSettings: {
      probeIntervalInSeconds: 30
      probePath: '/healthz'
      probeProtocol: 'Https'
      probeRequestType: 'GET'
    }
    loadBalancingSettings: {
      additionalLatencyInMilliseconds: 50
      sampleSize: 4
      successfulSamplesRequired: 3
    }
    sessionAffinityState: 'Enabled'
  }
}

resource frontDoorOrigin 'Microsoft.Cdn/profiles/originGroups/origins@2025-04-15' = if (!bootstrapMode) {
  parent: frontDoorOriginGroup
  name: 'gateway'
  properties: {
    enabledState: 'Enabled'
    enforceCertificateNameCheck: true
    hostName: gatewayApp!.properties.configuration.ingress.fqdn
    httpPort: 80
    httpsPort: 443
    originHostHeader: gatewayApp!.properties.configuration.ingress.fqdn
    priority: 1
    sharedPrivateLinkResource: {
      groupId: 'managedEnvironments'
      privateLink: {
        id: containerAppsEnvironment.id
      }
      privateLinkLocation: location
      requestMessage: 'MANOBAL Front Door private origin'
      status: 'Pending'
    }
    weight: 1000
  }
}

resource frontDoorRoute 'Microsoft.Cdn/profiles/afdEndpoints/routes@2025-04-15' = if (!bootstrapMode) {
  parent: frontDoorEndpoint
  name: 'all'
  properties: {
    enabledState: publicEndpointEnabled ? 'Enabled' : 'Disabled'
    forwardingProtocol: 'HttpsOnly'
    httpsRedirect: 'Enabled'
    linkToDefaultDomain: 'Enabled'
    originGroup: {
      id: frontDoorOriginGroup.id
    }
    patternsToMatch: [
      '/*'
    ]
    supportedProtocols: [
      'Http'
      'Https'
    ]
  }
  dependsOn: [
    frontDoorOrigin
  ]
}

resource wafPolicy 'Microsoft.Network/FrontDoorWebApplicationFirewallPolicies@2020-11-01' = if (!bootstrapMode) {
  name: wafPolicyName
  location: 'global'
  tags: commonTags
  sku: {
    name: 'Premium_AzureFrontDoor'
  }
  properties: {
    policySettings: {
      enabledState: 'Enabled'
      mode: wafMode
      requestBodyCheck: 'Enabled'
    }
    managedRules: {
      managedRuleSets: [
        {
          ruleSetType: 'DefaultRuleSet'
          ruleSetVersion: '2.1'
        }
        {
          ruleSetType: 'Microsoft_BotManagerRuleSet'
          ruleSetVersion: '1.1'
        }
      ]
    }
  }
}

resource frontDoorSecurityPolicy 'Microsoft.Cdn/profiles/securityPolicies@2021-06-01' = if (!bootstrapMode) {
  parent: frontDoorProfile
  name: 'waf'
  properties: {
    parameters: {
      associations: [
        {
          domains: [
            {
              id: frontDoorEndpoint.id
            }
          ]
          patternsToMatch: [
            '/*'
          ]
        }
      ]
      type: 'WebApplicationFirewall'
      wafPolicy: {
        id: wafPolicy.id
      }
    }
  }
}

resource budget 'Microsoft.Consumption/budgets@2024-08-01' = if (!empty(alertEmail)) {
  name: '${stem}-monthly-budget'
  properties: {
    amount: monthlyBudgetAmount
    category: 'Cost'
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: budgetStartDate
      endDate: dateTimeAdd(budgetStartDate, 'P2Y')
    }
    notifications: {
      Actual50: {
        contactEmails: [
          alertEmail
        ]
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 50
        thresholdType: 'Actual'
      }
      Actual80: {
        contactEmails: [
          alertEmail
        ]
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 80
        thresholdType: 'Actual'
      }
      Forecast100: {
        contactEmails: [
          alertEmail
        ]
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 100
        thresholdType: 'Forecasted'
      }
    }
  }
}

output AZURE_CONTAINER_REGISTRY_ENDPOINT string = registry.properties.loginServer
output AZURE_CONTAINER_REGISTRY_NAME string = registry.name
output RESOURCE_GROUP_NAME string = resourceGroup().name
output CONTAINER_APPS_ENVIRONMENT_NAME string = containerAppsEnvironment.name
output APP_KEY_VAULT_NAME string = appVault.name
output IDENTITY_KEY_VAULT_NAME string = identityVault.name
output STORAGE_ACCOUNT_NAME string = storage.name
output CORE_DATABASE_SERVER_NAME string = coreDb.name
output VAULT_DATABASE_SERVER_NAME string = vaultDb.name
output REDIS_NAME string = redis.name
output GATEWAY_APP_NAME string = bootstrapMode ? '' : gatewayName
output WEB_APP_NAME string = bootstrapMode ? '' : webName
output ENGINE_APP_NAME string = bootstrapMode ? '' : engineName
output ACUTE_APP_NAME string = bootstrapMode ? '' : acuteName
output VAULT_APP_NAME string = bootstrapMode ? '' : vaultName
output REALTIME_APP_NAME string = bootstrapMode ? '' : realtimeName
output CORE_MIGRATE_JOB_NAME string = bootstrapMode ? '' : coreMigrateJobName
output VAULT_MIGRATE_JOB_NAME string = bootstrapMode ? '' : vaultMigrateJobName
output SEED_JOB_NAME string = bootstrapMode ? '' : seedJobName
output FRONT_DOOR_PROFILE_NAME string = bootstrapMode ? '' : frontDoorProfileName
output FRONT_DOOR_ENDPOINT_NAME string = bootstrapMode ? '' : frontDoorEndpointName
output WEB_URL string = bootstrapMode ? '' : 'https://${frontDoorEndpoint!.properties.hostName}'
output ENGINE_URL string = bootstrapMode ? '' : 'https://${frontDoorEndpoint!.properties.hostName}'
output ENGINE_IDENTITY_CLIENT_ID string = engineIdentity.properties.clientId
output ENGINE_IDENTITY_PRINCIPAL_ID string = engineIdentity.properties.principalId
output VAULT_IDENTITY_CLIENT_ID string = vaultIdentity.properties.clientId
output CORE_MIGRATION_IDENTITY_CLIENT_ID string = coreMigrationIdentity.properties.clientId
output VAULT_MIGRATION_IDENTITY_CLIENT_ID string = vaultMigrationIdentity.properties.clientId
