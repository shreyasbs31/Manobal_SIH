"""Settings for the Zone 3 identity enclave.

This is a separate Django project from ``manobal-core``, not another app inside
it, and the separation is the point. §3.3 lists the identity resolver as one of
two components pulled out of the modular monolith, "because the entire privacy
model rests on the analytics code being *incapable* of resolving a token, not
merely declining to".

Two things follow, and both are visible below:

*   ``DATABASES`` contains ``iam_vault`` and nothing else. There is no alias
    here for ``org_store``, ``psy_store`` or ``gov_store``, so no code in this
    process can read the analytics plane even by mistake.
*   The analytics settings contain no alias for ``iam_vault`` and the analytics
    role does not exist in this cluster, so the reverse is true as well. The
    air-gap is symmetric.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Final

from django.core.exceptions import ImproperlyConfigured

BASE_DIR: Final = Path(__file__).resolve().parents[3]


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ImproperlyConfigured(
            f"{name} must be set. The identity enclave refuses to start on "
            f"defaults; a vault running with a guessable secret is worse than "
            f"a vault that is down."
        )
    return value


def _flag(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes"}


SECRET_KEY = _required("MANOBAL_IDENTITY_SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get("MANOBAL_IDENTITY_ALLOWED_HOSTS", "").split(",") if h.strip()
]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "manobal_identity.apps.vault",
]

REST_FRAMEWORK: dict[str, Any] = {
    "EXCEPTION_HANDLER": "manobal_identity.api.errors.problem_detail_handler",
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "manobal_identity.observability.middleware.RequestContextMiddleware",
]

ROOT_URLCONF = "manobal_identity.urls"
WSGI_APPLICATION = "manobal_identity.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "Asia/Kolkata"

# One database. Deliberately, and asserted by the privacy gate suite.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("MANOBAL_IDENTITY_DB_NAME", "iam_vault"),
        "USER": os.environ.get("MANOBAL_IDENTITY_DB_USER", "manobal_identity"),
        "PASSWORD": _required("MANOBAL_IDENTITY_DB_PASSWORD"),
        "HOST": os.environ.get("MANOBAL_IDENTITY_DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("MANOBAL_IDENTITY_DB_PORT", "55433"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"sslmode": os.environ.get("MANOBAL_IDENTITY_DB_SSLMODE", "require")},
    }
}

# Workload identities permitted to call this service, and what each may call.
# §4.9: "Only four workload identities may call it, and each may call only
# specific methods." In production these are SPIFFE IDs presented over mTLS;
# locally they are names carried on a header from the loopback interface.
WORKLOAD_SCOPES: dict[str, list[str]] = {
    "spiffe://manobal/ns/manobal-core/sa/ingest-worker": ["manobal.identity.tokenise"],
    "spiffe://manobal/ns/manobal-core/sa/core-api": ["manobal.identity.resolve"],
    "spiffe://manobal/ns/manobal-core/sa/alert-service": ["manobal.identity.resolve"],
    "spiffe://manobal/ns/manobal-core/sa/wdec-console": ["manobal.identity.breakglass"],
}

# Ed25519 public keys of the Zone 2 issuers whose grant assertions we honour,
# as base64 raw public keys keyed by key id. Rotation means adding a key here
# before Zone 2 starts signing with it.
GRANT_ISSUER_KEYS: dict[str, str] = dict(
    pair.split("=", 1)
    for pair in os.environ.get("MANOBAL_IDENTITY_GRANT_KEYS", "").split(",")
    if "=" in pair
)

REQUIRE_MTLS = _flag("MANOBAL_IDENTITY_REQUIRE_MTLS", True)

ENROLMENT = {
    "otp_per_mobile_hour": int(os.environ.get("MANOBAL_ENROLMENT_OTP_HOUR", "3")),
    "otp_per_mobile_day": int(os.environ.get("MANOBAL_ENROLMENT_OTP_DAY", "10")),
}

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31_536_000
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "no-referrer"
X_FRAME_OPTIONS = "DENY"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "redaction": {
            "()": "manobal_identity.observability.redaction.VaultRedactionFilter"
        }
    },
    # Zone 3 carries its own copy rather than importing the Zone 2 utility.
    # A shared logging helper would put `manobal_core` — and with it the
    # analytics settings and database code — inside the enclave's image, for
    # the sake of forty lines. §3.3 is worth more than the duplication.
    "formatters": {
        "json": {"()": "manobal_identity.observability.logging.JsonFormatter"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["redaction"],
        }
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get("MANOBAL_IDENTITY_LOG_LEVEL", "INFO"),
    },
}
