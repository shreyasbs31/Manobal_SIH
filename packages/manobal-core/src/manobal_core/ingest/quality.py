"""Write a data-quality row after each source-system batch (NFR-6.2)."""

from __future__ import annotations

from datetime import date

from manobal_core.apps.governance.models import DataQualityReport, IngestBatch


def record_hrms_quality(
    batch: IngestBatch, *, observed_on: date | None = None
) -> DataQualityReport:
    """Upsert today's completeness figures for ``batch.source_system``."""
    day = observed_on or batch.received_at.date()
    expected = batch.record_count
    received = batch.accepted_count
    quarantined = batch.quarantined_count
    report, _created = DataQualityReport.objects.update_or_create(
        source_system=batch.source_system,
        period_start=day,
        period_end=day,
        defaults={
            "expected_records": expected,
            "received_records": received,
            "quarantined_records": quarantined,
        },
    )
    return report
