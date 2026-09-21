#!/bin/sh
set -eu

environment_name=${1:-demo}

for command_name in az azd git docker; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Missing required command: ${command_name}" >&2
    exit 1
  fi
done

subscription_id=$(az account show --query id --output tsv)
account_state=$(az account show --query state --output tsv)
principal_id=$(az ad signed-in-user show --query id --output tsv)
account_email=$(az account show --query user.name --output tsv)

if [ "$account_state" != "Enabled" ]; then
  echo "The selected Azure subscription is not enabled." >&2
  exit 1
fi

roles=$(az role assignment list \
  --assignee-object-id "$principal_id" \
  --all \
  --include-inherited \
  --query "[].roleDefinitionName" \
  --output tsv)
if ! printf '%s\n' "$roles" | rg --quiet '^Owner$'; then
  echo "The signed-in account needs the Owner role for initial provisioning." >&2
  exit 1
fi

for provider in \
  Microsoft.App \
  Microsoft.ContainerRegistry \
  Microsoft.DBforPostgreSQL \
  Microsoft.Cache \
  Microsoft.KeyVault \
  Microsoft.Storage \
  Microsoft.Cdn \
  Microsoft.OperationalInsights \
  Microsoft.Insights \
  Microsoft.ManagedIdentity \
  Microsoft.Authorization; do
  state=$(az provider show --namespace "$provider" --query registrationState --output tsv)
  if [ "$state" != "Registered" ]; then
    echo "Azure provider is not registered: ${provider}" >&2
    exit 1
  fi
done

az resource show \
  --resource-group rg-manobal-ai \
  --name manobal-ai-resource \
  --resource-type Microsoft.CognitiveServices/accounts \
  --output none

failed_models=$(az cognitiveservices account deployment list \
  --resource-group rg-manobal-ai \
  --name manobal-ai-resource \
  --query "[?properties.provisioningState!='Succeeded'].name" \
  --output tsv)
if [ -n "$failed_models" ]; then
  echo "One or more existing Foundry deployments are not ready." >&2
  exit 1
fi

if ! azd env select "$environment_name" >/dev/null 2>&1; then
  azd env new "$environment_name"
fi

alert_email=${ALERT_EMAIL:-$account_email}
azd env set AZURE_SUBSCRIPTION_ID "$subscription_id"
azd env set AZURE_LOCATION centralindia
azd env set AZURE_PRINCIPAL_ID "$principal_id"
azd env set AZURE_PRINCIPAL_TYPE User
azd env set ALERT_EMAIL "$alert_email"
azd env set MONTHLY_BUDGET_AMOUNT "${MONTHLY_BUDGET_AMOUNT:-100000}"
azd env set AI_RESOURCE_GROUP rg-manobal-ai
azd env set BOOTSTRAP_MODE true
azd env set IMAGE_TAG bootstrap
azd env set PUBLIC_ENDPOINT_ENABLED false
azd env set WAF_MODE Detection

az bicep build --file infra/bicep/main.bicep --stdout >/dev/null

echo "Azure preflight passed for environment ${environment_name}."
echo "The first provision will keep application resources and the public route disabled."
