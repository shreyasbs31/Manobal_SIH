"""Record a scored instrument. Item answers are not written anywhere."""

from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from manobal_core.alerting.acute import raise_acute
from manobal_core.apps.governance.enums import DataType
from manobal_core.apps.governance.models import ConsentEntry, Subject
from manobal_core.apps.psystore.models import InstrumentResponse
from manobal_core.instruments.catalogue import SUPPORTED_LANGUAGES
from manobal_core.instruments.scoring import ScoredInstrument, score_answers


class InstrumentRefused(ValueError):  # noqa: N818
    """Consent missing, or the payload is not a completed instrument."""


@dataclass(frozen=True, slots=True)
class Submission:
    response: InstrumentResponse
    scored: ScoredInstrument


def submit_instrument(
    subject: Subject,
    *,
    code: str,
    language: str,
    answers: list[int],
    duration_seconds: int | None = None,
) -> Submission:
    """Score, persist the total, drop the answers, and raise T4 if item 9 fired."""
    if not ConsentEntry.current_for(subject.subject_token).get(DataType.SELF_REPORT):
        raise InstrumentRefused("self-report consent is required")
    language = language.lower()
    if language not in SUPPORTED_LANGUAGES:
        raise InstrumentRefused("language must be en or hi")
    scored = score_answers(code, answers, duration_seconds=duration_seconds)
    row = InstrumentResponse.objects.create(
        subject_token=subject.subject_token,
        instrument_code=scored.spec.code,
        instrument_version=scored.spec.version,
        language_code=language,
        completed_at=timezone.now(),
        total_score=scored.total,
        subscales={},
        duration_seconds=duration_seconds,
        straight_lined=scored.straight_lined,
        is_acute_flagged=scored.acute,
        acute_item_code=scored.acute_item_code,
    )
    if scored.acute:
        raise_acute(
            subject,
            signal_code=scored.acute_item_code,
            source="instrument",
            self_initiated=False,
        )
    return Submission(response=row, scored=scored)
