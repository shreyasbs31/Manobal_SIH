from __future__ import annotations

from django.apps import AppConfig


class PsyStoreConfig(AppConfig):
    """Instruments, check-ins and journals — the ``psy_store`` (D3, D5)."""

    name = "manobal_core.apps.psystore"
    label = "psystore"
    verbose_name = "Psychometric and self-report signals"
    default_auto_field = "django.db.models.BigAutoField"
