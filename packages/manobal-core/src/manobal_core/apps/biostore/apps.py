from __future__ import annotations

from django.apps import AppConfig


class BioStoreConfig(AppConfig):
    """Wearable physiological signals — the ``bio_store`` (D4). Awaiting TimescaleDB."""

    name = "manobal_core.apps.biostore"
    label = "biostore"
    verbose_name = "Physiological signals"
    default_auto_field = "django.db.models.BigAutoField"
