"""Unit-level critical incidents. No subject token lives here (UC-16)."""

from __future__ import annotations

from django.db import models
from django.utils import timezone


class UnitIncident(models.Model):
    """An operational incident that opens a 72-hour extra check-in window.

    The row is keyed by the unit, never by a person. Offering a check-in after
    a casualty or a high-intensity operation is a welfare courtesy, not a
    scoring input of its own — the check-in the person then files is.
    """

    id = models.BigAutoField(primary_key=True)
    unit = models.ForeignKey("governance.Unit", on_delete=models.CASCADE, related_name="incidents")
    occurred_at = models.DateTimeField(db_index=True)
    category = models.CharField(max_length=64)
    source_system = models.CharField(max_length=32, default="ops")
    external_id = models.CharField(max_length=64, blank=True, default="")
    window_hours = models.PositiveSmallIntegerField(default=72)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "unit_incident"
        ordering = ("-occurred_at",)
        indexes = [
            models.Index(fields=["unit", "-occurred_at"], name="unit_incide_unit_id_7c2a1e_idx")
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["source_system", "external_id"],
                condition=~models.Q(external_id=""),
                name="uniq_incident_external_id",
            )
        ]

    def __str__(self) -> str:
        return f"{self.unit_id} {self.category} @ {self.occurred_at:%Y-%m-%d}"
