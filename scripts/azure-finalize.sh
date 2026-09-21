#!/bin/sh
set -eu

resource_group=$(azd env get-value RESOURCE_GROUP_NAME)
app_vault=$(azd env get-value APP_KEY_VAULT_NAME)
identity_vault=$(azd env get-value IDENTITY_KEY_VAULT_NAME)
image_tag=$(azd env get-value IMAGE_TAG)

if [ -z "$image_tag" ] || [ "$image_tag" = "bootstrap" ]; then
  echo "Build release images before finalizing the environment." >&2
  exit 1
fi

for secret_name in \
  access-jwt \
  realtime-jwt \
  incident-hmac \
  grant-private-pem \
  judge-access-hash \
  operator-access-hash \
  demo-gate-jwt \
  deepgram-api-key \
  speech-key \
  translator-key \
  content-safety-key \
  acs-connection-string; do
  az keyvault secret show \
    --vault-name "$app_vault" \
    --name "$secret_name" \
    --query id \
    --output none
done

for secret_name in grant-public-pem vault-token-hmac tokenise-ingest; do
  az keyvault secret show \
    --vault-name "$identity_vault" \
    --name "$secret_name" \
    --query id \
    --output none
done

azd env set BOOTSTRAP_MODE false
azd env set PUBLIC_ENDPOINT_ENABLED false
azd provision --no-prompt

core_database=$(azd env get-value CORE_DATABASE_SERVER_NAME)
az postgres flexible-server restart \
  --resource-group "$resource_group" \
  --name "$core_database" \
  --output none

environment_name=$(azd env get-value CONTAINER_APPS_ENVIRONMENT_NAME)
attempt=0
while [ "$attempt" -lt 30 ]; do
  pending_ids=$(az network private-endpoint-connection list \
    --resource-group "$resource_group" \
    --name "$environment_name" \
    --type Microsoft.App/managedEnvironments \
    --query "[?properties.privateLinkServiceConnectionState.status=='Pending'].id" \
    --output tsv)
  if [ -n "$pending_ids" ]; then
    break
  fi
  attempt=$((attempt + 1))
  sleep 10
done

if [ -z "${pending_ids:-}" ]; then
  echo "No pending Front Door private endpoint connection was found." >&2
  echo "Approve it in the Container Apps environment before continuing." >&2
  exit 1
fi

printf '%s\n' "$pending_ids" | while IFS= read -r connection_id; do
  az network private-endpoint-connection approve \
    --id "$connection_id" \
    --description "MANOBAL Front Door private origin" \
    --output none
done

scripts/azure-run-job.sh \
  "$resource_group" \
  "$(azd env get-value CORE_MIGRATE_JOB_NAME)"
scripts/azure-run-job.sh \
  "$resource_group" \
  "$(azd env get-value VAULT_MIGRATE_JOB_NAME)"

vault_app=$(azd env get-value VAULT_APP_NAME)
attempt=0
while [ "$attempt" -lt 60 ]; do
  if az containerapp exec \
    --resource-group "$resource_group" \
    --name "$vault_app" \
    --command "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8100/health')\"" \
    >/dev/null 2>&1; then
    break
  fi
  attempt=$((attempt + 1))
  sleep 10
done
if [ "$attempt" -eq 60 ]; then
  echo "Vault did not become healthy after migration." >&2
  exit 1
fi

scripts/azure-run-job.sh \
  "$resource_group" \
  "$(azd env get-value SEED_JOB_NAME)"

engine_app=$(azd env get-value ENGINE_APP_NAME)
az containerapp exec \
  --resource-group "$resource_group" \
  --name "$engine_app" \
  --command "python -m app.providers.probe"

azd env set PUBLIC_ENDPOINT_ENABLED true
azd provision --no-prompt

echo "Azure deployment finalized."
echo "Judge URL: $(azd env get-value WEB_URL)"
