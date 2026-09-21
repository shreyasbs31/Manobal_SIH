FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/workspace/.venv/bin:$PATH" \
    PYTHONPATH="/workspace/services/synth"

RUN apt-get update \
    && apt-get install --yes --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY pyproject.toml uv.lock ./
COPY services/engine/pyproject.toml services/engine/pyproject.toml
COPY services/vault/pyproject.toml services/vault/pyproject.toml
COPY services/synth/pyproject.toml services/synth/pyproject.toml
RUN uv sync \
    --frozen \
    --no-dev \
    --package manobal-synth \
    --no-install-package manobal-synth

COPY services/synth services/synth

RUN useradd --create-home --uid 10003 manobal \
    && mkdir -p /workspace/services/synth/artifacts \
    && chown -R manobal:manobal /workspace/services/synth/artifacts
USER manobal
ENTRYPOINT ["python", "-m", "manobal_synth.cli"]
