from __future__ import annotations

from django.apps import AppConfig


class OrgStoreConfig(AppConfig):
    """Duty, leave and engagement features — the ``org_store`` (D1, D2, D7)."""

    name = "manobal_core.apps.orgstore"
    label = "orgstore"
    verbose_name = "Organisational signals"
    default_auto_field = "django.db.models.BigAutoField"
