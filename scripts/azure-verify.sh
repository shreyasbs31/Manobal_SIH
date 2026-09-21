#!/bin/sh
set -eu

web_url=$(azd env get-value WEB_URL)
resource_group=$(azd env get-value RESOURCE_GROUP_NAME)

if [ -z "$web_url" ]; then
  echo "The Azure web URL is not available." >&2
  exit 1
fi

restore_terminal() {
  stty echo </dev/tty 2>/dev/null || true
}
trap restore_terminal EXIT INT TERM

printf 'Judge access code: ' >/dev/tty
stty -echo </dev/tty
IFS= read -r judge_code </dev/tty
stty echo </dev/tty
printf '\n' >/dev/tty

printf 'Operator access code: ' >/dev/tty
stty -echo </dev/tty
IFS= read -r operator_code </dev/tty
stty echo </dev/tty
printf '\n' >/dev/tty

judge_cookies=$(mktemp)
operator_cookies=$(mktemp)
trap 'rm -f "$judge_cookies" "$operator_cookies"; restore_terminal' EXIT INT TERM
chmod 600 "$judge_cookies" "$operator_cookies"

attempt=0
while [ "$attempt" -lt 60 ]; do
  if curl \
    --fail \
    --silent \
    --show-error \
    --max-time 15 \
    "${web_url}/api/v1/system/health" \
    >/dev/null 2>&1; then
    break
  fi
  attempt=$((attempt + 1))
  sleep 10
done
if [ "$attempt" -eq 60 ]; then
  echo "The Front Door endpoint did not become healthy." >&2
  exit 1
fi

curl \
  --fail \
  --silent \
  --show-error \
  --cookie-jar "$judge_cookies" \
  --header 'content-type: application/json' \
  --data "{\"code\":\"${judge_code}\"}" \
  "${web_url}/api/v1/auth/demo-access" \
  >/dev/null

judge_director_status=$(curl \
  --silent \
  --output /dev/null \
  --write-out '%{http_code}' \
  --cookie "$judge_cookies" \
  --header 'content-type: application/json' \
  --data '{"role":"director","persona_id":null}' \
  "${web_url}/api/v1/auth/demo-login")
if [ "$judge_director_status" != "403" ]; then
  echo "Judge access unexpectedly reached the Director role." >&2
  exit 1
fi

curl \
  --fail \
  --silent \
  --show-error \
  --cookie-jar "$operator_cookies" \
  --header 'content-type: application/json' \
  --data "{\"code\":\"${operator_code}\"}" \
  "${web_url}/api/v1/auth/demo-access" \
  >/dev/null

curl \
  --fail \
  --silent \
  --show-error \
  --cookie "$operator_cookies" \
  --header 'content-type: application/json' \
  --data '{"role":"director","persona_id":null}' \
  "${web_url}/api/v1/auth/demo-login" \
  >/dev/null

gateway_app=$(azd env get-value GATEWAY_APP_NAME)
gateway_fqdn=$(az containerapp show \
  --resource-group "$resource_group" \
  --name "$gateway_app" \
  --query properties.configuration.ingress.fqdn \
  --output tsv)
if curl \
  --fail \
  --silent \
  --max-time 10 \
  "https://${gateway_fqdn}/healthz" \
  >/dev/null 2>&1; then
  echo "The private gateway was reachable without Front Door." >&2
  exit 1
fi

JUDGE_ACCESS_CODE="$judge_code" \
OPERATOR_ACCESS_CODE="$operator_code" \
WEB_URL="$web_url" \
ENGINE_URL="$web_url" \
AZURE_WEB_URL="$web_url" \
corepack pnpm --filter @manobal/e2e exec playwright test tests/demo-spine.spec.ts

azd env set WAF_MODE Prevention
azd provision --no-prompt

curl \
  --fail \
  --silent \
  --show-error \
  --max-time 15 \
  "${web_url}/api/v1/system/health" \
  >/dev/null

echo "Azure judge environment verification passed."
echo "Judge URL: ${web_url}"
