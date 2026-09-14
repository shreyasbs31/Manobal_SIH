"""Development settings for the local, non-Docker stack.

Every relaxation here is one that would be a defect in production, so each is
listed explicitly rather than folded into a ``DEBUG``-conditional block
somewhere in ``base``. Reading this file should tell an engineer exactly how far
their laptop differs from a deployment.

Notably *not* relaxed: the zone separation. There is still no ``iam_vault``
entry in ``DATABASES``, the local PostgreSQL clusters still reject
``manobal_core`` at the identity cluster's ``pg_hba``, and the risk engine still
runs with read-only grants. A development environment that lets you do things
production forbids will teach you habits production then rejects.
"""

from __future__ import annotations

import os
from pathlib import Path


def _load_env_file(path: Path) -> None:
    """Fill missing process env from a gitignored .env. Never overrides a real env."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            os.environ.setdefault(key, value)


_load_env_file(Path(__file__).resolve().parents[5] / ".env")


def _bootstrap_demo_llm() -> None:
    """Map Azure / OpenAI / xAI / Groq laptop secrets onto MANOBAL_LLM_*."""
    if os.environ.get("MANOBAL_LLM_API_KEY", "").strip():
        return
    azure = os.environ.get("AZURE_OPENAI_API_KEY", "").strip()
    azure_base = (
        os.environ.get("AZURE_OPENAI_ENDPOINT")
        or os.environ.get("AZURE_OPENAI_API_BASE")
        or ""
    ).strip()
    if azure and azure_base.startswith("https://"):
        os.environ["MANOBAL_LLM_API_KEY"] = azure
        os.environ.setdefault("MANOBAL_LLM_BASE_URL", azure_base)
        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "").strip()
        if deployment:
            os.environ.setdefault("MANOBAL_LLM_MODEL", deployment)
        version = os.environ.get("AZURE_OPENAI_API_VERSION", "").strip()
        if version:
            os.environ.setdefault("MANOBAL_LLM_API_VERSION", version)
        return
    openai = os.environ.get("OPENAI_API_KEY", "").strip()
    if openai:
        os.environ["MANOBAL_LLM_API_KEY"] = openai
        os.environ.setdefault(
            "MANOBAL_LLM_BASE_URL",
            os.environ.get("OPENAI_BASE_URL", "").strip() or "https://api.openai.com/v1",
        )
        return
    xai = (os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY") or "").strip()
    if xai:
        os.environ["MANOBAL_LLM_API_KEY"] = xai
        os.environ.setdefault("MANOBAL_LLM_BASE_URL", "https://api.x.ai/v1")
        os.environ.setdefault("MANOBAL_LLM_MODEL", "grok-4-fast")
        return
    groq = os.environ.get("GROQ_API_KEY", "").strip()
    if groq:
        os.environ["MANOBAL_LLM_API_KEY"] = groq
        os.environ.setdefault("MANOBAL_LLM_BASE_URL", "https://api.groq.com/openai/v1")
        os.environ.setdefault("MANOBAL_LLM_MODEL", "llama-3.1-8b-instant")


_bootstrap_demo_llm()

# Set before importing base, whose _required() reads the environment at import
# time. These are development-only values and are never used elsewhere: the
# local clusters are bound to loopback and hold synthetic data exclusively.
os.environ.setdefault("MANOBAL_ENV", "dev")
os.environ.setdefault("MANOBAL_SECRET_KEY", "dev-only-not-a-secret-do-not-deploy")
os.environ.setdefault("MANOBAL_DB_PASSWORD", "dev_only_not_a_secret")
os.environ.setdefault("MANOBAL_DB_HOST", "127.0.0.1")
os.environ.setdefault("MANOBAL_DB_PORT", "55432")
os.environ.setdefault("MANOBAL_DB_SSLMODE", "disable")
os.environ.setdefault("MANOBAL_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")
# The signed-ruleset requirement is the one control it is genuinely impractical
# to keep on locally, since it would require every developer to hold the signing
# key — which would defeat the purpose of having one.
os.environ.setdefault("MANOBAL_RULESET_REQUIRE_SIGNATURE", "false")
# Set through the environment rather than by mutating LOGGING after the import.
# base.py already reads this variable, so one place decides the level instead of
# two that can drift apart.
os.environ.setdefault("MANOBAL_LOG_LEVEL", "DEBUG")
# Fixed development seeds. They sign synthetic receipts and grant assertions.
os.environ.setdefault(
    "MANOBAL_ERASURE_SIGNING_KEY",
    __import__("base64").b64encode(b"\x33" * 32).decode(),
)
os.environ.setdefault(
    "MANOBAL_GRANT_SIGNING_KEY",
    __import__("base64").b64encode(b"\x44" * 32).decode(),
)
os.environ.setdefault("MANOBAL_GRANT_KEY_ID", "core-dev")
os.environ.setdefault("MANOBAL_IDENTITY_URL", "http://127.0.0.1:8001")
os.environ.setdefault("MANOBAL_HELPLINE_FORCE", "1800-123-4567")
os.environ.setdefault("MANOBAL_AGENT_BACKEND", "auto")
os.environ.setdefault(
    "MANOBAL_JOURNAL_MASTER_KEY",
    __import__("base64").b64encode(b"\x55" * 32).decode(),
)

from .base import *  # noqa: E402, F403

DEBUG = True
LOCAL_ISSUER_ENABLED = True
# Phone / Expo Go on the LAN must reach this process. Laptop-only.
ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = [
    "https://*.ngrok-free.dev",
    "https://*.ngrok.io",
    "https://*.exp.direct",
    "https://*.trycloudflare.com",
    "https://*.lhr.life",
    "https://*.localhost.run",
    "https://*.pinggy.link",
]
if os.environ.get("MANOBAL_CELERY_EAGER", "1") in {"1", "true", "yes"}:
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True

# TLS terminates at the ingress in a deployment; there is no ingress on a laptop.
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# A local Ed25519 issuer stands in for Keycloak so the authorisation path is
# exercised end to end. It mints the same claim set — role, force, unit, amr —
# so a bug in the predicates surfaces here rather than in staging.
OIDC = {
    **OIDC,  # noqa: F405
    "ISSUER": "https://localhost/manobal-dev",
    "AUDIENCE": "manobal-core",
    "JWKS_URL": "http://127.0.0.1:8000/dev/jwks",
    "ALGORITHMS": ["RS256"],
}

IDENTITY_RESOLVER = {
    **IDENTITY_RESOLVER,  # noqa: F405
    "BASE_URL": os.environ.get("MANOBAL_IDENTITY_URL", "http://127.0.0.1:8001"),
    "CA_BUNDLE": "",
}
