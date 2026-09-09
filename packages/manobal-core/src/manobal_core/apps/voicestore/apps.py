from __future__ import annotations

from django.apps import AppConfig


class VoiceStoreConfig(AppConfig):
    """Vocal-acoustic features — the ``voice_store`` (D6). Awaiting pgvector."""

    name = "manobal_core.apps.voicestore"
    label = "voicestore"
    verbose_name = "Vocal-acoustic signals"
    default_auto_field = "django.db.models.BigAutoField"
