FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/workspace/.venv/bin:$PATH" \
    PYTHONPATH="/workspace/services/engine"

WORKDIR /workspace
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml uv.lock ./
COPY services/engine/pyproject.toml services/engine/pyproject.toml
COPY services/vault/pyproject.toml services/vault/pyproject.toml
COPY services/synth/pyproject.toml services/synth/pyproject.toml
RUN uv sync \
    --frozen \
    --no-dev \
    --package manobal-engine \
    --no-install-package manobal-engine

COPY infra/rulesets /workspace/infra/rulesets
COPY infra/ai /workspace/infra/ai
COPY infra/prompts /workspace/infra/prompts
COPY infra/lexicon /workspace/infra/lexicon
COPY infra/corpus /workspace/infra/corpus
COPY infra/evals /workspace/infra/evals
COPY infra/i18n /workspace/infra/i18n
COPY services/engine services/engine

RUN useradd --create-home --uid 10001 manobal
USER manobal
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
