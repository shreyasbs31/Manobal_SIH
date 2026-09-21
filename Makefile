SHELL := /bin/sh
COMPOSE := docker compose --env-file infra/.env -f infra/docker-compose.yml

.PHONY: up down logs migrate seed reset contracts copy-lint test eval eval-live e2e deploy verify dev lint twa infra-ready providers-check providers-missing foundry-token translate-catalog audio-generate voice-latency azure-preflight azure-provision azure-secrets azure-build azure-finalize azure-verify azure-suspend azure-pin-token-key

up:
	$(COMPOSE) up --build --detach --wait --wait-timeout 600

foundry-token:
	mkdir -p infra/.cache
	if [ -d infra/.cache/foundry.token ]; then rm -rf infra/.cache/foundry.token; fi
	az account get-access-token --resource https://cognitiveservices.azure.com --query accessToken -o tsv > infra/.cache/foundry.token.tmp \
		&& mv infra/.cache/foundry.token.tmp infra/.cache/foundry.token \
		|| rm -f infra/.cache/foundry.token.tmp
	if [ ! -e infra/.cache/foundry.token ]; then : > infra/.cache/foundry.token; fi

infra-ready: foundry-token
	$(COMPOSE) up --detach --wait --wait-timeout 180 core-db vault-db redis
	$(COMPOSE) exec -T core-db pg_isready -U core_owner -d manobal_core
	$(COMPOSE) exec -T vault-db pg_isready -U vault_owner -d manobal_vault
	$(COMPOSE) exec -T redis redis-cli ping

dev: infra-ready
	$(COMPOSE) up --build --detach --wait --wait-timeout 600

providers-missing:
	PYTHONPATH=services/engine uv run python -c "from app.config import get_settings; print(', '.join(get_settings().missing_live_provider_names()) or 'none')"

providers-check: foundry-token
	@if $(COMPOSE) ps --status running -q engine 2>/dev/null | grep -q .; then \
		$(COMPOSE) exec -T engine python -m app.providers.probe; \
	else \
		PYTHONPATH=services/engine:services/vault uv run python scripts/providers-check.py; \
	fi

lint:
	corepack pnpm --recursive lint

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs --follow

migrate:
	$(COMPOSE) run --rm --no-deps core-migrate
	$(COMPOSE) run --rm --no-deps vault-migrate

seed:
	$(COMPOSE) --profile tools run --rm synth seed

reset:
	$(COMPOSE) down --volumes --remove-orphans
	$(MAKE) up
	$(MAKE) seed

contracts:
	PYTHONPATH=services/engine uv run python -m app.openapi
	corepack pnpm --filter @manobal/contracts generate

copy-lint:
	python3 scripts/copy-lint

test: copy-lint
	PYTHONPATH=services/engine uv run pytest services/engine/tests \
		--cov=app.scoring --cov=app.privacy --cov-fail-under=90
	PYTHONPATH=services/vault uv run pytest services/vault/tests
	PYTHONPATH=services/synth uv run pytest services/synth/tests
	corepack pnpm --recursive typecheck
	corepack pnpm --filter @manobal/ui test
	corepack pnpm --filter @manobal/contracts test
	corepack pnpm --filter @manobal/illustrations test
	PYTHONPATH=services/engine uv run pytest infra/evals

eval:
	PYTHONPATH=services/engine uv run pytest infra/evals

eval-live:
	LIVE_EVALS=1 PYTHONPATH=services/engine uv run pytest infra/evals/test_live_routing.py infra/evals/test_retrieval.py -q

translate-catalog:
	PYTHONPATH=services/engine uv run python scripts/translate-catalog.py

audio-generate:
	PYTHONPATH=services/engine uv run python -c "from app.audio import generate_audio; print(generate_audio())"

voice-latency:
	PYTHONPATH=services/engine uv run python scripts/voice-latency.py

e2e:
	corepack pnpm --filter @manobal/e2e test

azure-preflight:
	./scripts/azure-preflight.sh demo

azure-provision:
	azd provision --no-prompt

azure-secrets:
	PYTHONPATH=services/engine uv run --package manobal-engine python scripts/azure-secrets.py \
		--app-vault "$$(azd env get-value APP_KEY_VAULT_NAME)" \
		--identity-vault "$$(azd env get-value IDENTITY_KEY_VAULT_NAME)"

azure-build:
	./scripts/azure-build-images.sh

azure-finalize:
	./scripts/azure-finalize.sh

azure-verify:
	./scripts/azure-verify.sh

azure-suspend:
	./scripts/azure-suspend.sh

azure-pin-token-key:
	./scripts/azure-pin-token-key.sh

deploy: azure-finalize

verify: copy-lint
	python3 scripts/verify-foundation.py

twa:
	test -f apps/twa/twa-manifest.json
	python3 -c "import json; json.load(open('apps/twa/twa-manifest.json'))"
