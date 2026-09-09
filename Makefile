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

typecheck: ## mypy --strict on the Python packages (NFR-M2)
	$(MYPY) packages/manobal-risk/src

test: ## Run every fast test suite
	$(PYTEST) packages -m "not integration and not slow"

test-risk: ## Risk engine only, with its 90% gate (NFR-M3)
	$(PYTEST) packages/manobal-risk --cov=manobal_risk \
		--cov-report=term-missing --cov-fail-under=90

gates: lint typecheck test-risk ## Everything CI runs before a merge

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
