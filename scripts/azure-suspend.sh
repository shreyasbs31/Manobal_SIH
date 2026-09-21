#!/bin/sh
set -eu

resource_group=$(azd env get-value RESOURCE_GROUP_NAME)

azd env set PUBLIC_ENDPOINT_ENABLED false
azd provision --no-prompt

for variable_name in \
  GATEWAY_APP_NAME \
  WEB_APP_NAME \
  ENGINE_APP_NAME \
  ACUTE_APP_NAME \
  VAULT_APP_NAME \
  REALTIME_APP_NAME; do
  app_name=$(azd env get-value "$variable_name")
  az containerapp update \
    --resource-group "$resource_group" \
    --name "$app_name" \
    --min-replicas 0 \
    --max-replicas 1 \
    --output none
done

for variable_name in CORE_DATABASE_SERVER_NAME VAULT_DATABASE_SERVER_NAME; do
  server_name=$(azd env get-value "$variable_name")
  az postgres flexible-server stop \
    --resource-group "$resource_group" \
    --name "$server_name" \
    --output none
done

echo "The public route is disabled and pausable compute has been stopped."
echo "Managed Redis, Front Door, storage, and retained data can still incur charges."
