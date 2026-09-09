# MANOBAL — developer entry points.
#
# SDD §8.2 requires that an engineer can bring the whole system up with one
# command on day three. `make dev` is that command.

SHELL := /bin/bash
PY := .venv/bin/python
PIP := .venv/bin/pip
RUFF := .venv/bin/ruff
MYPY := .venv/bin/mypy
PYTEST := .venv/bin/python -m pytest

RULESET := rulesets/manobal-ruleset-1.0.0.yaml

.DEFAULT_GOAL := help
.PHONY: help venv install lint format typecheck test test-risk coverage gates \
        ruleset-keygen ruleset-sign ruleset-verify ruleset-show clean

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

venv: ## Create the workspace virtualenv (Python 3.12)
	python3.12 -m venv .venv && $(PIP) install --upgrade pip

install: venv ## Install every package editable into the workspace venv
	$(PIP) install -e packages/manobal-risk[dev]
	$(PIP) install ruff mypy types-PyYAML

lint: ## ruff check across every package (NFR-M2)
	$(RUFF) check packages

format: ## ruff format in place
	$(RUFF) format packages

# Two invocations, because django-stubs resolves model types from a settings
# module and there is one per config file. The enclave's settings deliberately
# do not know about the analytics apps, nor the reverse.
typecheck: ## mypy --strict on the Python packages (NFR-M2)
	$(MYPY) packages/manobal-risk/src packages/manobal-core/src packages/manobal-synth/src
	$(MYPY) --config-file packages/manobal-identity/mypy.ini packages/manobal-identity/src

test: test-zone2 test-zone3 ## Run every fast test suite

test-zone2: ## Analytics plane, plus the enclave's pure-logic suites
	$(PYTEST) packages -m "not integration and not slow"

# Django settings are process-global, so Zone 3 cannot share a session with
# Zone 2. Its database-backed tests run here, against test_iam_vault.
test-zone3: ## Identity enclave, against its own vault database
	$(PYTEST) packages/manobal-identity/tests/enclave \
		-o DJANGO_SETTINGS_MODULE=manobal_identity.settings.test \
		-p no:cacheprovider

test-risk: ## Risk engine only, with its 90% gate (NFR-M3)
	$(PYTEST) packages/manobal-risk --cov=manobal_risk \
		--cov-report=term-missing --cov-fail-under=90

gates: lint typecheck test-risk test ## Everything CI runs before a merge

ruleset-keygen: ## Generate a development ruleset signing keypair
	$(PY) -m manobal_risk.cli keygen

ruleset-sign: ## Sign the current ruleset artefact (needs MANOBAL_RULESET_SIGNING_KEY)
	$(PY) -m manobal_risk.cli sign $(RULESET)

ruleset-verify: ## Verify the ruleset signature (needs MANOBAL_RULESET_VERIFY_KEY)
	$(PY) -m manobal_risk.cli verify $(RULESET)

ruleset-show: ## Print a reviewable summary of the ruleset
	$(PY) -m manobal_risk.cli show $(RULESET)

clean: ## Remove caches and build artefacts
	find . -type d \( -name __pycache__ -o -name .pytest_cache -o -name .ruff_cache \
		-o -name .mypy_cache -o -name '*.egg-info' \) -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov coverage.xml

# ------------------------------------------------------------ local stores --
PG_SCRIPT := packages/manobal-infra/scripts/local_pg.sh

db-up: ## Start the local analytics + identity PostgreSQL clusters
	@$(PG_SCRIPT) up

db-down: ## Stop both clusters
	@$(PG_SCRIPT) down

db-reset: ## Destroy and re-provision both clusters
	@$(PG_SCRIPT) reset

db-status: ## Show cluster state and zone assignment
	@$(PG_SCRIPT) status

db-extensions: ## Apply TimescaleDB/pgvector where available (unlocks bio + voice stores)
	@/opt/homebrew/opt/postgresql@16/bin/psql -p 55432 -d postgres \
		-v ON_ERROR_STOP=1 -f packages/manobal-infra/postgres/analytics-extensions.sql

.PHONY: db-up db-down db-reset db-status db-extensions
