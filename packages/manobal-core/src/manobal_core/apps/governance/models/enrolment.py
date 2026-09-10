"""Device pairing and the journal key that lives outside the psych store.

The journal ciphertext is in ``psy_store``. The key that opens it is here, in
the governance store, so erasing the key leaves a restored psy backup unreadable.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone


class JournalKey(models.Model):
    """Per-subject data key, wrapped under the process master key."""

    id = models.BigAutoField(primary_key=True)
    subject_token = models.CharField(max_length=64, db_index=True)
    key_id = models.CharField(max_length=64, unique=True)
    wrapped_key = models.BinaryField()
    created_at = models.DateTimeField(default=timezone.now)
    destroyed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "journal_key"
        indexes = [
            models.Index(
                fields=["subject_token", "destroyed_at"],
                name="journal_key_subject_d_idx",
            )
        ]

    def __str__(self) -> str:
        return self.key_id


class PairedDevice(models.Model):
    """A personnel device bound to a token. Holds no service number or name."""

    id = models.BigAutoField(primary_key=True)
    subject_token = models.CharField(max_length=64, db_index=True)
    device_id = models.CharField(max_length=64)
    public_key = models.CharField(max_length=512)
    paired_at = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "paired_device"
        constraints = [
            models.UniqueConstraint(
                fields=["subject_token", "device_id"], name="uniq_paired_device"
            )
        ]
        indexes = [
            models.Index(
                fields=["subject_token", "revoked_at"],
                name="paired_devi_subject_r_idx",
            )
        ]

    def __str__(self) -> str:
        return f"{self.subject_token} {self.device_id}"

    @property
    def is_live(self) -> bool:
        return self.revoked_at is None
