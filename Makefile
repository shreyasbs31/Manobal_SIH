SHELL := /bin/sh
COMPOSE := docker compose --env-file infra/.env -f infra/docker-compose.yml

.PHONY: up down logs migrate seed reset contracts copy-lint test eval eval-live e2e deploy verify dev lint twa infra-ready providers-check providers-missing foundry-token translate-catalog audio-generate voice-latency

up:
	$(COMPOSE) up --build --detach --wait --wait-timeout 600

foundry-token:
	mkdir -p infra/.cache
	touch infra/.cache/foundry.token
	az account get-access-token --resource https://cognitiveservices.azure.com --query accessToken -o tsv > infra/.cache/foundry.token 2>/dev/null || true

infra-ready: foundry-token
	$(COMPOSE) up --detach --wait --wait-timeout 180 core-db vault-db redis
	$(COMPOSE) exec -T core-db pg_isready -U core_owner -d manobal_core
	$(COMPOSE) exec -T vault-db pg_isready -U vault_owner -d manobal_vault
	$(COMPOSE) exec -T redis redis-cli ping

dev: infra-ready
	$(COMPOSE) up --build --detach --wait --wait-timeout 600

providers-missing:
	PYTHONPATH=services/engine uv run python -c "from app.config import get_settings; print(', '.join(get_settings().missing_live_provider_names()) or 'none')"

providers-check:
	PYTHONPATH=services/engine:services/vault uv run python scripts/providers-check.py

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
	LIVE_EVALS=1 PYTHONPATH=services/engine uv run pytest infra/evals/test_live_routing.py -q

translate-catalog:
	PYTHONPATH=services/engine uv run python scripts/translate-catalog.py

audio-generate:
	PYTHONPATH=services/engine uv run python -c "from app.audio import generate_audio; print(generate_audio())"

voice-latency:
	PYTHONPATH=services/engine uv run python scripts/voice-latency.py

e2e:
	corepack pnpm --filter @manobal/e2e test

deploy:
	azd up

verify: copy-lint
	python3 scripts/verify-foundation.py

twa:
	test -f apps/twa/twa-manifest.json
	python3 -c "import json; json.load(open('apps/twa/twa-manifest.json'))"
