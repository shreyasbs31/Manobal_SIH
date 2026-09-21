# MANOBAL Azure judge deployment

This runbook deploys the complete synthetic MANOBAL demonstration to Azure and produces one
protected HTTPS link for hackathon judges.

This environment is a shared demonstration sandbox. It is not approved for real personnel,
real cases, or operational use.

## 1. What this deployment creates

The existing AI resource group remains unchanged:

- `rg-manobal-ai`
- Microsoft Foundry and its model deployments in East US 2
- Azure AI Speech in Central India
- Azure AI Translator in Central India
- Azure AI Content Safety in East US 2
- Azure Communication Services with India data location

The deployment creates a separate runtime resource group:

- Azure Front Door Premium with WAF
- A private Container Apps environment in Central India
- Gateway, web, engine, vault, realtime, and acute Container Apps
- Core migration, vault migration, and synthetic seed jobs
- Azure Container Registry
- Two PostgreSQL Flexible Servers
- Azure Managed Redis
- An application Key Vault
- A separate Premium Key Vault for identity-vault cryptography
- Blob storage
- Application Insights and Log Analytics
- A monthly cost budget

The runtime resource group references the existing AI resources. Deleting the runtime resource
group does not delete `rg-manobal-ai`.

## 2. Security model

The browser only reaches Azure Front Door.

Front Door reaches one private gateway through Private Link. The gateway routes requests inside
the Container Apps environment:

- `/` and normal page routes go to the Next.js web app.
- `/api/v1/*` goes to the FastAPI engine.
- `/api/v1/voice/session` upgrades to the engine voice WebSocket.
- `/realtime/*` upgrades to the realtime service.

The engine, vault, web, and realtime Container Apps have internal ingress. Their generated
Container Apps hostnames are not public product URLs.

The public demonstration has two access levels:

- Judge access permits the ordinary synthetic personnel and officer roles.
- Operator access additionally permits Director and System Admin.

Access codes are entered through secure terminal prompts. Only scrypt hashes are stored in Key
Vault. Do not put either code in source files, shell history, chat, or GitHub.

## 3. Important limitations

The engine and realtime service contain process-local demonstration state. They intentionally run
with one replica each. Multiple replicas would produce inconsistent judge sessions.

The environment is shared. Actions performed by one judge can change synthetic state observed by
another judge. Director reset is restricted to the operator.

The fast Director reset clears process-local demo state. The full synthetic seed job is a separate
operator action.

Passkeys are not part of the judge release. They are tied to the final hostname and their current
server-side storage is process-local.

## 4. Local prerequisites

Required commands:

```bash
az --version
azd version
docker version
git --version
corepack pnpm --version
uv --version
```

Sign in:

```bash
az login
azd auth login
```

Select the subscription containing the Azure credits:

```bash
az account list --output table
az account set --subscription "<subscription shown by Azure>"
```

Do not paste the subscription identifier into chat. It is stored in the local azd environment.

## 5. Local release gate

Before provisioning:

```bash
make test
make lint
git diff --check
az bicep build --file infra/bicep/main.bicep --stdout >/dev/null
```

The deployment build requires a clean Git tree so every image maps to one immutable commit.

Generated video files, screenshots, `.azure`, provider settings, keys, caches, and archives must
remain untracked.

## 6. Configure the azd environment

Run:

```bash
make azure-preflight
```

The preflight performs masked checks only. It:

- Verifies the Azure subscription is enabled.
- Verifies the signed-in principal has the Owner role.
- Verifies required Azure providers are registered.
- Verifies the existing Foundry resource and deployments.
- Creates or selects the local `demo` azd environment.
- Selects Central India for the runtime.
- Records the deployer object identifier.
- Configures a monthly budget value.
- Keeps bootstrap mode on.
- Keeps the public Front Door route off.
- Keeps WAF in Detection mode.
- Compiles the Bicep template.

Review the local environment names without printing secret values:

```bash
azd env list
azd env get-value AZURE_LOCATION
azd env get-value AI_RESOURCE_GROUP
azd env get-value BOOTSTRAP_MODE
azd env get-value PUBLIC_ENDPOINT_ENABLED
```

## 7. Review the infrastructure change

Run a preview before creating resources:

```bash
azd provision --preview
```

Confirm that the preview targets a new MANOBAL runtime resource group and references
`rg-manobal-ai` as existing infrastructure.

Do not proceed if the preview proposes deleting or replacing an existing AI resource.

## 8. Provision the foundation

This step creates billable Azure resources:

```bash
make azure-provision
```

Bootstrap mode creates networking, identities, databases, Redis, registries, Key Vaults, storage,
logging, and the Container Apps environment. Application containers and the public Front Door route
remain disabled.

Provisioning PostgreSQL, Managed Redis, and Container Apps can take time. A long-running Azure
operation is not automatically a failure.

Confirm the outputs:

```bash
azd env get-value RESOURCE_GROUP_NAME
azd env get-value AZURE_CONTAINER_REGISTRY_NAME
azd env get-value APP_KEY_VAULT_NAME
azd env get-value IDENTITY_KEY_VAULT_NAME
```

These are resource names, not secret values.

## 9. Populate Key Vault

Run this in your own terminal:

```bash
make azure-secrets
```

The command:

- Loads existing provider settings through the approved settings loader.
- Retrieves Azure provider keys only when a local value is absent.
- Never prints a value.
- Generates JWT and HMAC material in memory.
- Generates a new Ed25519 grant key pair in memory.
- Stores private and public grant material in separate vaults.
- Prompts for a judge code.
- Prompts for a different operator code.
- Stores only the code hashes.

Codes must contain at least 12 characters and may use letters, numbers, period, underscore, and
hyphen.

Save both codes in a password manager. Share only the judge code with judges.

Re-running the command preserves generated internal secrets. Provider secrets are refreshed.
Access codes are preserved unless `--rotate-access` is explicitly used.

## 10. Create an immutable source checkpoint

Inspect the source tree:

```bash
git status --short
git diff --check
```

Commit the reviewed application and deployment source. Do not commit provider files or generated
artifacts.

The release image tag has the form:

```text
git-<12 character commit id>
```

## 11. Build images remotely

Run:

```bash
make azure-build
```

The command submits six remote linux/amd64 builds to Azure Container Registry:

- Gateway
- Web
- Engine
- Vault
- Realtime
- Synthetic seed tooling

Remote builds are required because the development Mac uses Apple Silicon and Azure runs
linux/amd64 containers.

Each image uses the same immutable Git tag. The tag is saved into the azd environment after every
build succeeds.

## 12. Create the applications and data

Run:

```bash
make azure-finalize
```

The finalization sequence is intentionally ordered:

1. Verify every required Key Vault secret name exists.
2. Turn bootstrap mode off.
3. Provision the real Container Apps, jobs, Front Door, and WAF.
4. Restart core PostgreSQL after loading TimescaleDB.
5. Approve the pending Front Door private connection.
6. Run the core migration job.
7. Run the vault migration job.
8. Wait for the vault health check.
9. Run the deterministic synthetic seed job.
10. Run the live provider probe inside the Azure engine container.
11. Enable the Front Door route.
12. Print the judge URL.

If a job fails, stop. Do not enable the public route. Inspect the failed execution:

```bash
az containerapp job execution list \
  --resource-group "$(azd env get-value RESOURCE_GROUP_NAME)" \
  --name "$(azd env get-value CORE_MIGRATE_JOB_NAME)" \
  --output table
```

Use the corresponding vault or seed job name when checking another job.

## 13. Verify the public release

Run:

```bash
make azure-verify
```

The verification command securely asks for both access codes and then checks:

- Front Door health.
- Judge access succeeds.
- Judge access cannot mint a Director session.
- Operator access can mint a Director session.
- The private gateway cannot be reached directly.
- The Playwright demo spine passes against Azure.
- The reset succeeds between runs.
- WAF is moved from Detection to Prevention.
- Health remains green after WAF enforcement.

The access codes are passed only to the verification child process. They are not printed or written
to a file.

## 14. Judge handoff

Retrieve the shareable URL:

```bash
azd env get-value WEB_URL
```

Send judges:

- The HTTPS URL.
- The judge access code through a separate private channel.
- A short note that all people and cases are synthetic.

Do not send:

- The operator code.
- Azure identifiers.
- Key Vault names.
- Provider settings.
- Database hostnames.

Immediately before judging:

1. Sign in with the operator code.
2. Open Director.
3. Run Reset.
4. Run Warm up.
5. Confirm provider tiles are healthy.
6. Test one voice turn.
7. Sign out of the operator session.

## 15. Monitoring

Useful commands:

```bash
az containerapp list \
  --resource-group "$(azd env get-value RESOURCE_GROUP_NAME)" \
  --output table

az containerapp logs show \
  --resource-group "$(azd env get-value RESOURCE_GROUP_NAME)" \
  --name "$(azd env get-value ENGINE_APP_NAME)" \
  --follow
```

Never use a log command that prints environment variables or secret values.

Monitor:

- Front Door 5xx responses.
- WAF blocks.
- Container restarts.
- Engine provider fallbacks and 429 responses.
- PostgreSQL CPU, storage, and connection count.
- Redis memory and connectivity.
- Voice latency.
- Azure credit expiry.

Azure budgets are alerting tools. They do not stop resources and their cost data can be delayed.

## 16. Suspend after judging

Run:

```bash
make azure-suspend
```

This:

- Disables the Front Door route.
- Scales Container Apps down where supported.
- Stops both PostgreSQL servers.

Managed Redis, Front Door, storage, Key Vault retention, and retained data can still incur charges.

Azure automatically restarts a stopped PostgreSQL Flexible Server after its maximum stop period.
Delete the runtime environment if it is no longer needed.

## 17. Full teardown

First confirm the selected azd environment:

```bash
azd env list
azd env get-value RESOURCE_GROUP_NAME
```

Then remove the runtime environment:

```bash
azd down
```

The existing AI resource group is referenced as external infrastructure and is not part of this
teardown.

Key Vault purge protection intentionally retains deleted vaults for the retention period. Do not
attempt to bypass purge protection.

## 18. Rollback

Every release uses an immutable image tag. Record the working tag:

```bash
azd env get-value IMAGE_TAG
```

If a new release fails:

1. Disable the public route.
2. Restore the previous `IMAGE_TAG`.
3. Re-run `azd provision`.
4. Do not downgrade database migrations automatically.
5. Run health and E2E checks.
6. Re-enable the route only after verification.

Schema migrations must remain backward compatible with the previous application image.

## 19. Common failures

### Key Vault reference fails

Check:

- The secret name exists.
- The Container App has the intended user-assigned identity.
- The identity has Key Vault Secrets User.
- RBAC propagation has completed.

Do not print the secret to test it.

### PostgreSQL login fails

Check:

- Entra authentication is enabled.
- The migration identity is the server administrator.
- The bootstrap job created the application principal.
- The URL contains the managed identity name.
- TLS is required.
- Private DNS resolves from the Container Apps environment.

### Voice WebSocket fails

Check:

- Front Door route caching is disabled.
- Gateway is healthy.
- `/api/v1/voice/session` reaches the engine.
- Browser microphone permission is allowed.
- CSP permits same-origin WSS.

### Realtime updates fail

Check:

- `/realtime/*` reaches the realtime app.
- Engine and realtime use the same realtime JWT secret.
- Realtime has exactly one replica.

### Front Door returns 504

Check the private connection status:

```bash
az network private-endpoint-connection list \
  --resource-group "$(azd env get-value RESOURCE_GROUP_NAME)" \
  --name "$(azd env get-value CONTAINER_APPS_ENVIRONMENT_NAME)" \
  --type Microsoft.App/managedEnvironments \
  --output table
```

The connection must be Approved before the route can serve traffic.

## 20. Real-user warning

Do not reuse this judge environment for real users.

A real-user pilot requires a custom domain, complete officer identity integration, durable passkey
storage, removal of demo login and Director controls, externalized process state, multi-replica
testing, formal data-residency review, security testing, and an approved operational support model.
