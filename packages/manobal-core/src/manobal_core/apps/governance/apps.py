from __future__ import annotations

from django.apps import AppConfig


class GovernanceConfig(AppConfig):
    """Consent, audit, casework and assessment records — the ``gov_store``."""

    name = "manobal_core.apps.governance"
    label = "governance"
    verbose_name = "Governance and consent"
    default_auto_field = "django.db.models.BigAutoField"
