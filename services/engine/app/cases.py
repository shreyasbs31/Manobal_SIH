from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from .auth import PERSONAS
from .config import get_settings
from .sim_clock import wall_seconds_for_sla

TIER_SLA_MINUTES = {"T4": 15, "T3": 24 * 60, "T2": 72 * 60, "T1": 7 * 24 * 60, "T0": 14 * 24 * 60}
ESCALATION = (
    "uwo",
    "company_welfare_deputy",
    "battalion_mo",
    "sector_counsellor",
)


@dataclass
class CaseRecord:
    case_id: str
    token: str
    unit_path: str
    tier: str
    status: str
    opened_at: datetime
    sla_due_at: datetime
    dominant_domains: list[str]
    recommended: list[str]
    source: str
    trajectory: str = "stable"
    limited: bool = False
    ack_at: datetime | None = None


@dataclass
class AlertRecord:
    id: str
    case_id: str
    tier: str
    recipient: str
    channel: str
    status: str
    at: datetime
    ack_at: datetime | None = None


@dataclass
class EscalationRecord:
    case_id: str
    step: str
    recipient: str
    due_at: datetime
    fired_at: datetime | None = None
    ack_at: datetime | None = None


CASES: dict[str, CaseRecord] = {}
ALERTS: list[AlertRecord] = []
ESCALATIONS: list[EscalationRecord] = []
LEDGER: list[dict[str, str]] = []


def sla_due(tier: str, opened: datetime) -> datetime:
    minutes = TIER_SLA_MINUTES.get(tier, 24 * 60)
    wall = wall_seconds_for_sla(minutes * 60)
    return opened + timedelta(seconds=wall)


def remaining_ratio(case: CaseRecord, now: datetime | None = None) -> float:
    current = now or datetime.now(UTC)
    total = (case.sla_due_at - case.opened_at).total_seconds() or 1.0
    left = (case.sla_due_at - current).total_seconds()
    return max(0.0, min(1.0, left / total))


def open_case(
    *,
    case_id: str,
    token: str,
    unit_path: str,
    tier: str,
    domains: list[str],
    recommended: list[str],
    source: str,
    trajectory: str = "stable",
    limited: bool = False,
    now: datetime | None = None,
) -> CaseRecord:
    opened = now or datetime.now(UTC)
    record = CaseRecord(
        case_id=case_id,
        token=token,
        unit_path=unit_path,
        tier=tier,
        status="open",
        opened_at=opened,
        sla_due_at=sla_due(tier, opened),
        dominant_domains=domains,
        recommended=recommended,
        source=source,
        trajectory=trajectory,
        limited=limited,
    )
    CASES[case_id] = record
    if tier in {"T2", "T3", "T4"}:
        dispatch_alerts(record)
        if tier == "T4":
            seed_escalation(record)
    return record


def dispatch_alerts(case: CaseRecord) -> list[AlertRecord]:
    created: list[AlertRecord] = []
    recipients = ["uwo"]
    if case.tier == "T4":
        recipients.append("mo")
    for recipient in recipients:
        for channel in ("inapp", "sms", "call") if case.tier == "T4" else ("inapp", "digest"):
            alert = AlertRecord(
                id=f"{case.case_id}:{recipient}:{channel}",
                case_id=case.case_id,
                tier=case.tier,
                recipient=recipient,
                channel=channel,
                status="dispatched",
                at=case.opened_at,
            )
            ALERTS.append(alert)
            created.append(alert)
    return created


def seed_escalation(case: CaseRecord) -> None:
    compression = get_settings().sim_time_compression
    first = 5 * 60 / compression
    for index, step in enumerate(ESCALATION):
        ESCALATIONS.append(
            EscalationRecord(
                case_id=case.case_id,
                step=step,
                recipient=step,
                due_at=case.opened_at + timedelta(seconds=first * (index + 1)),
            )
        )


def acknowledge(case_id: str, actor: str, now: datetime | None = None) -> CaseRecord:
    case = CASES[case_id]
    stamp = now or datetime.now(UTC)
    case.ack_at = stamp
    case.status = "acknowledged"
    for alert in ALERTS:
        if alert.case_id == case_id and alert.recipient in {actor, "uwo", "mo"}:
            alert.status = "ack"
            alert.ack_at = stamp
    for step in ESCALATIONS:
        if step.case_id == case_id and step.ack_at is None:
            step.ack_at = stamp
            break
    return case


def digest_items() -> list[CaseRecord]:
    return [
        case for case in CASES.values() if case.tier in {"T2", "T3"} and case.status != "closed"
    ]


def queue_items(scope_path: str) -> list[CaseRecord]:
    return [case for case in CASES.values() if case.unit_path.startswith(scope_path)]


def persona_case_id(token: str) -> str | None:
    for persona in PERSONAS.values():
        if persona.token == token:
            return persona.case_id
    return None
