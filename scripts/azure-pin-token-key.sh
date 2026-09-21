#!/bin/sh
# Pin the Azure identity vault's token HMAC key to the local demo key.
#
# Why: the eight demo personas carry hard-coded subject tokens that were derived
# with the local key in infra/keys/dev-vault-keys.json. The synthetic seed refuses
# to run unless the vault reproduces exactly those tokens, so the Azure vault must
# use the same token key. This environment holds synthetic data only.
#
# The key value is never printed. It travels through a 0600 temporary file that is
# removed on exit. The previous secret version is kept in Key Vault for rollback.
set -eu

key_file=${1:-infra/keys/dev-vault-keys.json}

if [ ! -f "$key_file" ]; then
  echo "Local key file not found: $key_file" >&2
  exit 1
fi

identity_vault=$(azd env get-value IDENTITY_KEY_VAULT_NAME)
resource_group=$(azd env get-value RESOURCE_GROUP_NAME)
vault_app=$(azd env get-value VAULT_APP_NAME)

temp_file=$(mktemp)
chmod 600 "$temp_file"
trap 'rm -f "$temp_file"' EXIT INT TERM

python3 - "$key_file" >"$temp_file" <<'PY'
import base64
import json
import sys

value = json.load(open(sys.argv[1], encoding="utf-8"))["token_hmac_key"]
if len(base64.b64decode(value, validate=True)) != 32:
    raise SystemExit("token_hmac_key must decode to 32 bytes")
sys.stdout.write(value)
PY

previous_version=$(az keyvault secret show \
  --vault-name "$identity_vault" \
  --name vault-token-hmac \
  --query id \
  --output tsv)

az keyvault secret set \
  --vault-name "$identity_vault" \
  --name vault-token-hmac \
  --file "$temp_file" \
  --encoding utf-8 \
  --output none

echo "vault-token-hmac updated. Previous version (rollback reference): $previous_version"

# The vault caches the token key in memory, so restart it to load the new version.
revision=$(az containerapp show \
  --resource-group "$resource_group" \
  --name "$vault_app" \
  --query properties.latestRevisionName \
  --output tsv)
az containerapp revision restart \
  --resource-group "$resource_group" \
  --name "$vault_app" \
  --revision "$revision" \
  --output none

echo "Vault restarted on revision ${revision}."
echo "Next: clear stale vault identities from the failed seed, then re-run the seed job."
