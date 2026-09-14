"""The T4 path: one function, no queue, vital interest (SDD §4.7).

This is the only place consent, corroboration and the nightly window are
overridden. It records the signal and persists a T4 assessment, which opens
the case, authorises resolution, and pages the accountable officers. It does
not counsel, and it does not wait.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from django.utils import timezone

from manobal_core.apps.governance.models import Case, Subject
from manobal_core.apps.psystore.models import AcuteSignal
from manobal_core.scoring.orchestrator import persist_assessment
from manobal_risk.types import Domain, RiskAssessment
from manobal_risk.types import Tier as EngineTier


@dataclass(frozen=True, slots=True)
class AcuteResult:
    signal: AcuteSignal
    case: Case | None


def raise_acute(
    subject: Subject,
    *,
    signal_code: str,
    source: str,
    self_initiated: bool = False,
    now: datetime | None = None,
) -> AcuteResult:
    """Record the trigger, force T4, and page the accountable officers."""
    moment = now or timezone.now()
    signal = AcuteSignal.objects.create(
        subject_token=subject.subject_token,
        detected_at=moment,
        signal_code=signal_code,
        source=source,
        self_initiated=self_initiated,
    )
    persisted = persist_assessment(_forced_t4(subject.subject_token, moment), subject)
    AcuteSignal.objects.filter(pk=signal.pk).update(dispatched_at=timezone.now())
    signal.refresh_from_db()
    return AcuteResult(signal=signal, case=persisted.case)


def _forced_t4(token: str, moment: datetime) -> RiskAssessment:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return RiskAssessment(
        subject_token=token,
        assessed_at=moment,
        tier=EngineTier.T4,
        tier_before_hysteresis=EngineTier.T4,
        contributing_categories=("immediate_safety_indicator", "self_reported_wellbeing"),
        contributing_domains=(Domain.SELF_REPORT,),
        domain_coverage=tuple((domain, domain is Domain.SELF_REPORT) for domain in Domain),
        ruleset_version="acute-override",
        ruleset_sha256="e" * 64,
        corroborated=True,
        acute_override=True,
        insufficient_coverage=False,
    )
