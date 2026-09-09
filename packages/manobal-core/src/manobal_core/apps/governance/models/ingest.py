"""Ingestion provenance, quarantine and data-quality reporting (SDD §4.1, §5.3).

A welfare system that silently accepts bad data produces confident nonsense about
real people. The rule applied here is that malformed input is quarantined and
visible, never coerced into shape: a duty roster with a corrupted shift length is
held for a human, not rounded to something plausible and scored.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone


class IngestBatch(models.Model):
    """One delivery from one source system.

    ``contract_version`` is checked before parsing, not after. Source systems in
    this environment change their exports without warning, and detecting that at
    the schema boundary produces "HRMS sent us v2, we speak v1" rather than a
    week of quietly wrong leave balances.
    """

    id = models.BigAutoField(primary_key=True)
    source_system = models.CharField(max_length=32, db_index=True)
    contract_version = models.CharField(max_length=16)
    received_at = models.DateTimeField(default=timezone.now, db_index=True)

    #: Digest of the raw payload, for reconciliation with the source and to make
    #: a redelivery of identical content cheap to detect.
    payload_digest = models.CharField(max_length=64)
    record_count = models.PositiveIntegerField(default=0)
    accepted_count = models.PositiveIntegerField(default=0)
    quarantined_count = models.PositiveIntegerField(default=0)

    status = models.CharField(
        max_length=16,
        choices=[
            ("received", "Received"),
            ("validated", "Validated"),
            ("applied", "Applied"),
            ("rejected", "Rejected"),
        ],
        default="received",
    )
    error_summary = models.TextField(blank=True, default="")

    class Meta:
        db_table = "ingest_batch"
        ordering = ("-received_at",)

    def __str__(self) -> str:
        return f"{self.source_system}@{self.received_at:%Y-%m-%d %H:%M}"


class QuarantinedRecord(models.Model):
    """A record that failed validation, held for human resolution (§4.1).

    The payload is stored *tokenised*. A record can fail validation and still
    contain a service number, and letting bad data smuggle an identifier into the
    analytics plane through the error path would defeat the boundary the whole
    architecture is built around. Tokenisation happens before validation for
    exactly this reason.
    """

    id = models.BigAutoField(primary_key=True)
    batch = models.ForeignKey(IngestBatch, on_delete=models.CASCADE, related_name="quarantined")
    subject_token = models.CharField(max_length=64, null=True, blank=True, db_index=True)

    reason_code = models.CharField(max_length=48, db_index=True)
    reason_detail = models.TextField()
    payload = models.JSONField(default=dict, blank=True)

    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.CharField(max_length=128, blank=True, default="")
    resolution = models.CharField(
        max_length=16,
        choices=[
            ("pending", "Pending"),
            ("reprocessed", "Corrected and reprocessed"),
            ("discarded", "Discarded"),
        ],
        default="pending",
    )

    class Meta:
        db_table = "quarantined_record"
        ordering = ("-id",)
        indexes = [models.Index(fields=["resolution", "reason_code"])]


class CaptureReceipt(models.Model):
    """Proof that a device's batch was accepted, for at-most-once application.

    Personnel devices operate on intermittent connectivity (NFR-1.4) and retry.
    ``client_batch_id`` is unique so a retried upload is recognised and
    acknowledged rather than double-counted: a check-in applied twice would shift
    a personal baseline by fabricated evidence.
    """

    id = models.BigAutoField(primary_key=True)
    subject_token = models.CharField(max_length=64, db_index=True)
    client_batch_id = models.CharField(max_length=64, unique=True)
    received_at = models.DateTimeField(default=timezone.now)

    item_count = models.PositiveIntegerField(default=0)
    accepted_count = models.PositiveIntegerField(default=0)
    #: Items dropped because the person has not consented to that data type.
    rejected_unconsented = models.PositiveIntegerField(default=0)
    #: Items dropped as stale. A three-week-old reading from a phone that was in
    #: a drawer says nothing about how someone is today.
    rejected_stale = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "capture_receipt"
        ordering = ("-received_at",)


class DataQualityReport(models.Model):
    """Periodic completeness and freshness per source (§10.2, NFR-6.2).

    Coverage gaps are reported rather than imputed. If a wearable feed stops, the
    honest system response is "we do not know", handled by coverage
    renormalisation in the engine — not a filled-in value that produces a
    confident tier from data that does not exist.
    """

    id = models.BigAutoField(primary_key=True)
    source_system = models.CharField(max_length=32, db_index=True)
    period_start = models.DateField()
    period_end = models.DateField()

    expected_records = models.PositiveIntegerField(default=0)
    received_records = models.PositiveIntegerField(default=0)
    quarantined_records = models.PositiveIntegerField(default=0)
    #: Delay between the event and its arrival. A feed that is complete but four
    #: days late cannot support the T4 response window.
    median_lag_hours = models.FloatField(null=True, blank=True)

    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "data_quality_report"
        ordering = ("-period_end",)
        constraints = [
            models.UniqueConstraint(
                fields=["source_system", "period_start", "period_end"], name="uniq_dq_period"
            )
        ]

    @property
    def completeness(self) -> float | None:
        if not self.expected_records:
            return None
        return self.received_records / self.expected_records
