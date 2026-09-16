SHELL := /bin/sh
COMPOSE := docker compose --env-file infra/.env -f infra/docker-compose.yml

.PHONY: up down logs migrate seed reset contracts copy-lint test eval e2e deploy verify dev lint

up:
	$(COMPOSE) up --build --detach --wait --wait-timeout 600

dev: up

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

e2e:
	corepack pnpm --filter @manobal/e2e test

deploy:
	azd up

verify: copy-lint
	python3 scripts/verify-foundation.py
