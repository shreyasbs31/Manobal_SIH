#!/bin/sh
# Verify the open judge deployment (no access gate; the site opens on /stage).
set -eu

web_url=$(azd env get-value WEB_URL)
resource_group=$(azd env get-value RESOURCE_GROUP_NAME)

if [ -z "$web_url" ]; then
  echo "The Azure web URL is not available." >&2
  exit 1
fi

attempt=0
while [ "$attempt" -lt 60 ]; do
  if curl --fail --silent --max-time 15 "${web_url}/api/v1/system/health" >/dev/null 2>&1; then
    break
  fi
  attempt=$((attempt + 1))
  sleep 10
done
if [ "$attempt" -eq 60 ]; then
  echo "The Front Door endpoint did not become healthy." >&2
  exit 1
fi

root_target=$(curl --silent --output /dev/null --max-time 15 \
  --write-out '%{redirect_url}' "${web_url}/")
case "$root_target" in
  */stage) ;;
  *)
    echo "The site root does not redirect to /stage (got: ${root_target:-none})." >&2
    exit 1
    ;;
esac

# Stage signs in as Director, so an open deployment must allow it without a code.
curl --fail --silent --show-error --max-time 30 \
  --header 'content-type: application/json' \
  --data '{"role":"director","persona_id":null}' \
  "${web_url}/api/v1/auth/demo-login" >/dev/null

gateway_app=$(azd env get-value GATEWAY_APP_NAME)
gateway_fqdn=$(az containerapp show \
  --resource-group "$resource_group" \
  --name "$gateway_app" \
  --query properties.configuration.ingress.fqdn \
  --output tsv)
if curl --fail --silent --max-time 10 "https://${gateway_fqdn}/healthz" >/dev/null 2>&1; then
  echo "The private gateway was reachable without Front Door." >&2
  exit 1
fi

WEB_URL="$web_url" \
ENGINE_URL="$web_url" \
AZURE_WEB_URL="$web_url" \
corepack pnpm --filter @manobal/e2e exec playwright test tests/demo-spine.spec.ts

if [ "$(azd env get-value WAF_MODE)" != "Prevention" ]; then
  azd env set WAF_MODE Prevention
  azd provision --no-prompt
fi

curl --fail --silent --show-error --max-time 15 "${web_url}/api/v1/system/health" >/dev/null

echo "Azure judge environment verification passed."
echo "Judge URL: ${web_url}/stage"
