"""Score every active subject against the signed ruleset (M4/M5 nightly)."""

from __future__ import annotations

from django.conf import settings

from manobal_core.apps.governance.enums import SubjectStatus
from manobal_core.apps.governance.models import Subject
from manobal_core.interventions.lookup import propose_for_case
from manobal_core.scoring.features import assemble_history
from manobal_core.scoring.orchestrator import persist_assessment
from manobal_risk import load_ruleset, score


def score_subject(subject: Subject) -> None:
    """Assemble history, score, persist. No numeric score is stored."""
    history = assemble_history(subject.subject_token)
    ruleset = load_ruleset(
        settings.RULESET_PATH,
        require_signature=bool(settings.RULESET_REQUIRE_SIGNATURE),
    )
    engine = score(history, ruleset)
    result = persist_assessment(engine, subject)
    if result.case is not None and result.grant is not None:
        propose_for_case(result.case)


def score_all_subjects() -> int:
    """Score every active subject. Returns how many were assessed."""
    counted = 0
    for subject in Subject.objects.filter(status=SubjectStatus.ACTIVE).select_related("unit"):
        score_subject(subject)
        counted += 1
    return counted
