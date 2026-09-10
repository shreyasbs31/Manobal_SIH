"""A person may contest a flag. The assessment itself is never rewritten (FR-4.5)."""

from __future__ import annotations

from django.utils import timezone

from manobal_core.apps.governance.enums import CaseStatus
from manobal_core.apps.governance.models import Case


class ContestRefused(ValueError):  # noqa: N818
    """The case is not theirs, or it is already closed."""


def contest_case(case: Case, *, subject_token: str, note: str) -> Case:
    """Mark the case contested. Does not touch the immutable assessment."""
    if case.subject_token != subject_token:
        raise ContestRefused("you may only contest your own flag")
    if not case.is_open:
        raise ContestRefused("a closed case cannot be contested")
    text = note.strip()
    if not text:
        raise ContestRefused("a contest note is required")
    case.contested_at = timezone.now()
    case.contest_note = text[:2000]
    case.status = CaseStatus.CONTESTED
    case.save(update_fields=["contested_at", "contest_note", "status"])
    return case
