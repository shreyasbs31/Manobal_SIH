FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/workspace/.venv/bin:$PATH" \
    PYTHONPATH="/workspace/services/engine"

WORKDIR /workspace
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
COPY services/engine services/engine

RUN useradd --create-home --uid 10001 manobal
USER manobal
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
