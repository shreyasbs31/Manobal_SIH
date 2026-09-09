"""App configuration for the identity vault."""

from __future__ import annotations

from django.apps import AppConfig


class VaultConfig(AppConfig):
    name = "manobal_identity.apps.vault"
    label = "vault"
    verbose_name = "Identity vault (Zone 3)"
    default_auto_field = "django.db.models.BigAutoField"
