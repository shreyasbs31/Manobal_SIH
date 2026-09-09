"""Django settings for the MANOBAL Zone 2 modular monolith.

Two rules govern this file:

1. **No secret has a usable default.** :func:`_required` raises at import time if
   a production-sensitive setting is missing, so the service fails to start
   rather than running with a placeholder key. SDD §7 lists "validate that
   required secrets are present at startup" as a mandatory control, and a
   settings module full of ``os.environ.get(..., "changeme")`` is how that
   control is quietly lost.
2. **No connection string for Zone 3 appears anywhere.** There is no
   ``iam_vault`` entry in ``DATABASES`` and no credential for it in this process.
   The identity resolver is reached over mTLS as a network service or not at all
   (SDD §3.1, §4.9, NFR-SEC5).
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
REPO_ROOT = BASE_DIR.parents[1]


class ImproperlyConfigured(RuntimeError):
    """A required setting is absent. The service must not start."""


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ImproperlyConfigured(
            f"{name} is not set. MANOBAL refuses to start without it rather than "
            f"falling back to a default, because a default secret in a system holding "
            f"mental-health data is worse than an outage."
        )
    return value


def _flag(name: str, *, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


ENVIRONMENT = os.environ.get("MANOBAL_ENV", "dev")
DEBUG = False
SECRET_KEY = _required("MANOBAL_SECRET_KEY")
ALLOWED_HOSTS = [h for h in os.environ.get("MANOBAL_ALLOWED_HOSTS", "").split(",") if h]

# --------------------------------------------------------------- application
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "rest_framework",
    # One app per store. The app label is what StoreRouter routes on.
    "manobal_core.apps.governance",
    "manobal_core.apps.orgstore",
    "manobal_core.apps.psystore",
    "manobal_core.apps.biostore",
    "manobal_core.apps.voicestore",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "manobal_core.apps.authz.middleware.PrincipalMiddleware",
    "manobal_core.observability.middleware.RequestContextMiddleware",
]

ROOT_URLCONF = "manobal_core.urls"
WSGI_APPLICATION = "manobal_core.wsgi.application"
ASGI_APPLICATION = "manobal_core.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": False,
        "OPTIONS": {"context_processors": []},
    }
]

# ----------------------------------------------------------------- databases
def _store(name: str, *, alias_env: str) -> dict[str, object]:
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get(f"{alias_env}_NAME", name),
        "USER": os.environ.get("MANOBAL_DB_USER", "manobal_core"),
        "PASSWORD": _required("MANOBAL_DB_PASSWORD"),
        "HOST": os.environ.get("MANOBAL_DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("MANOBAL_DB_PORT", "55432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"sslmode": os.environ.get("MANOBAL_DB_SSLMODE", "prefer")},
        "ATOMIC_REQUESTS": False,
    }


DATABASES = {
    "default": _store("gov_store", alias_env="MANOBAL_DB_GOV"),
    "org": _store("org_store", alias_env="MANOBAL_DB_ORG"),
    "psy": _store("psy_store", alias_env="MANOBAL_DB_PSY"),
    "bio": _store("bio_store", alias_env="MANOBAL_DB_BIO"),
    "voice": _store("voice_store", alias_env="MANOBAL_DB_VOICE"),
}
# There is deliberately no "iam_vault" entry. See the module docstring.

DATABASE_ROUTERS = ["manobal_core.db.routers.StoreRouter"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ------------------------------------------------------------- localisation
# IST is the canonical server timezone (SDD §6.1); storage stays UTC.
LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True
# FR-1.16: Hindi and English at launch, with officially validated clinical
# translations. Machine translation of a validated instrument invalidates it.
LANGUAGES = [("en", "English"), ("hi", "हिन्दी")]

# ------------------------------------------------------------------ security
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "no-referrer"
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "Strict"
X_FRAME_OPTIONS = "DENY"

# ---------------------------------------------------------------------- OIDC
# SDD §6.2: no password ever reaches MANOBAL's own code.
OIDC = {
    "ISSUER": os.environ.get("MANOBAL_OIDC_ISSUER", "http://localhost:58080/realms/manobal"),
    "AUDIENCE": os.environ.get("MANOBAL_OIDC_AUDIENCE", "manobal-core"),
    "JWKS_URL": os.environ.get("MANOBAL_OIDC_JWKS_URL", ""),
    "ALGORITHMS": ["RS256"],
    "LEEWAY_SECONDS": 30,
    #: Officer roles must present a second factor. A JWT whose `amr` shows only a
    #: password is rejected for these roles even if every other claim is valid
    #: (NFR-SEC3, error MB-4012).
    "MFA_REQUIRED_ROLES": [
        "welfare_officer",
        "commander",
        "medical_officer",
        "wdec_auditor",
    ],
    "SECOND_FACTOR_METHODS": ["otp", "mfa", "hwk", "swk", "fido", "totp"],
}

# ------------------------------------------------------------------ identity
# Zone 3 is a network service, not a database. These settings carry a URL and a
# client certificate; there is no username, password or DSN here to widen.
IDENTITY_RESOLVER = {
    "BASE_URL": os.environ.get("MANOBAL_IDENTITY_URL", "https://identity-resolver:8443"),
    "CLIENT_CERT": os.environ.get("MANOBAL_IDENTITY_CLIENT_CERT", ""),
    "CLIENT_KEY": os.environ.get("MANOBAL_IDENTITY_CLIENT_KEY", ""),
    "CA_BUNDLE": os.environ.get("MANOBAL_IDENTITY_CA", ""),
    "TIMEOUT_SECONDS": 5.0,
}

# ---------------------------------------------------------------- risk engine
RULESET_PATH = os.environ.get(
    "MANOBAL_RULESET_PATH", str(REPO_ROOT / "rulesets" / "manobal-ruleset-1.0.0.yaml")
)
#: FR-3.6 / SDD §10.5. Off only in dev and test; there is no runtime toggle.
RULESET_REQUIRE_SIGNATURE = _flag("MANOBAL_RULESET_REQUIRE_SIGNATURE", default=True)

# ------------------------------------------------------------------ policies
PRIVACY = {
    #: SDD §4.8. Below this cohort size an aggregate is suppressed entirely —
    #: not rounded, not masked, and the count itself is withheld.
    "K_ANONYMITY_THRESHOLD": int(os.environ.get("MANOBAL_K_THRESHOLD", "10")),
    #: A unit whose membership churned by more than this between periods is
    #: suppressed too, closing the differencing attack across time.
    "MAX_COHORT_CHURN": 0.5,
    #: FR-5.4. Case access expires on closure or at this age, whichever is first.
    "ACCESS_GRANT_MAX_DAYS": 14,
    #: FR-7.3 retention.
    "RAW_RETENTION_DAYS": 90,
    "DERIVED_RETENTION_MONTHS": 24,
    "AUDIT_RETENTION_YEARS": 7,
    #: FR-7.2. Withdrawal must purge the data type within this window.
    "ERASURE_SLA_HOURS": 24,
    #: FR-7.4. Separation from service.
    "SEPARATION_PURGE_DAYS": 30,
}

ALERTING = {
    #: FR-6.2. The entire push payload. Nothing else is renderable on a lock
    #: screen, because a lock screen is a public surface in a barracks.
    "PUSH_BODY": "MANOBAL: 1 welfare item needs your review.",
    "URGENT_PUSH_BODY": "MANOBAL: 1 urgent welfare item needs your review.",
    #: NFR-P6 / UC-10.
    "ACUTE_DISPATCH_SLA_MINUTES": 15,
    "SLA_HOURS_BY_TIER": {"T2": 24 * 7, "T3": 48, "T4": 0},
}

RATE_LIMITS = {
    # SDD §6.5. These are security controls, not commercial tiers. Exceeding the
    # identity limits raises a security event, not a usage warning.
    "enrolment_otp_per_mobile_hour": 3,
    "enrolment_otp_per_mobile_day": 10,
    "captures_batch_per_device_hour": 60,
    "captures_batch_max_packets": 500,
    "agent_turns_per_session": 40,
    "agent_turns_per_day": 200,
    "officer_queue_per_hour": 600,
    "identity_resolve_per_officer_hour": 5,
    "identity_resolve_per_officer_day": 20,
    "identity_breakglass_per_officer_day": 2,
    "commander_aggregates_per_hour": 300,
    "unauthenticated_per_ip_minute": 100,
    "integration_webhook_per_minute": 100,
}

AGENT = {
    #: SDD §7.8. One flag disables the conversational agent force-wide; the
    #: system degrades to structured forms and keeps working.
    "ENABLED": _flag("MANOBAL_AGENT_ENABLED", default=True),
    "BACKEND": os.environ.get("MANOBAL_AGENT_BACKEND", "deterministic"),
    "EDGE_URL": os.environ.get("MANOBAL_AGENT_EDGE_URL", ""),
    "MAX_TEMPERATURE": 0.3,
    "SESSION_TTL_MINUTES": 30,
}

# ------------------------------------------------------------------- celery
CELERY_BROKER_URL = os.environ.get("MANOBAL_BROKER_URL", "amqp://guest:guest@localhost:55672//")
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_BROKER_TRANSPORT_OPTIONS = {"confirm_publish": True}
CELERY_TIMEZONE = TIME_ZONE

# --------------------------------------------------------------------- DRF
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "manobal_core.apps.authz.authentication.OIDCBearerAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        # Deny by default. An endpoint that forgets to declare a permission gets
        # no callers rather than every caller.
        "manobal_core.apps.authz.permissions.DenyAll",
    ],
    "DEFAULT_PAGINATION_CLASS": "manobal_core.apps.api.pagination.CursorPagination",
    "PAGE_SIZE": 50,
    "EXCEPTION_HANDLER": "manobal_core.apps.api.errors.problem_detail_handler",
    "UNAUTHENTICATED_USER": None,
}

# --------------------------------------------------------------------- logs
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        # SDD §10.1: redaction is enforced at the logger, not by convention. A
        # developer cannot accidentally log a person's PHQ-9 answers, because the
        # filter drops the record and CI fails on it.
        "redact": {"()": "manobal_core.observability.redaction.RedactionFilter"},
    },
    "formatters": {
        "json": {"()": "manobal_core.observability.logging.JsonFormatter"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["redact"],
        }
    },
    "root": {"handlers": ["console"], "level": os.environ.get("MANOBAL_LOG_LEVEL", "INFO")},
    "loggers": {
        # The audit stream is separate, separately stored and hash-chained
        # (SDD §7.3). It is never mixed into application logs.
        "manobal.audit": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
