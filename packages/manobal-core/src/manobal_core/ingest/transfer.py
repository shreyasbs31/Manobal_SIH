"""Revoke prior officer access when a person changes posting (FR-7.5)."""

from __future__ import annotations

from manobal_core.apps.governance.enums import SubjectStatus
from manobal_core.apps.governance.models import Subject, Unit
from manobal_core.erasure.stores import revoke_live_grants_for_subject


def apply_posting_change(
    existing: Subject | None,
    *,
    new_unit: Unit,
    employment_status: str,
) -> None:
    """Revoke live grants before the new unit is written.

    A posting change is either an explicit ``transferred`` status or a unit
    code that is no longer the one on the subject row. The person stays
    ``ACTIVE`` at the new unit so nightly scoring continues; only an explicit
    transfer flag parks them as ``TRANSFERRED`` when they have left observation.
    """
    if existing is None:
        return
    status = employment_status.strip().lower()
    unit_changed = existing.unit_id != new_unit.code
    if not unit_changed and status != SubjectStatus.TRANSFERRED:
        return
    revoke_live_grants_for_subject(existing.subject_token)
    if status == SubjectStatus.TRANSFERRED and not unit_changed:
        existing.status = SubjectStatus.TRANSFERRED
        existing.save(update_fields=["status"])
