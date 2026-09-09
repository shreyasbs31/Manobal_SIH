"""Output row types — one frozen dataclass per output file.

``ObservationRow`` is a contract, not a convenience. Its four fields are exactly
``manobal_risk.Observation`` plus the subject token, so a generated corpus loads
into the risk engine with a dict unpack and no adapter. If the engine's type
changes, ``test_risk_engine_integration.py`` stops compiling, which is the
intended alarm.

The split across files mirrors the production separation of concerns rather than
being a tidying decision. Identifying attributes live in ``subjects.jsonl``,
observations carry a token and nothing else, and the injected truth lives in a
third file that no scoring path is ever given. A loader that only reads
``observations.jsonl`` and ``consent.jsonl`` is holding exactly what SDD §3.2
allows the analytics plane to hold.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, timezone
from typing import Any

#: Indian Standard Time. Every timestamp the platform records is local to the
#: force, and a synthetic corpus in UTC would hide off-by-one-day errors in every
#: nightly-batch boundary the pipeline has.
IST = timezone(timedelta(hours=5, minutes=30), name="IST")

#: Hour at which a self-raised acute event is timestamped. Late evening, which is
#: when in-app crisis traffic actually arrives and when the on-call rota is
#: thinnest — a detail worth having in load fixtures.
_ACUTE_HOUR = 21
_INCIDENT_HOUR = 14


def at_ist(day: date, hour: int) -> datetime:
    return datetime.combine(day, time(hour=hour), tzinfo=IST)


def now_utc() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True, slots=True)
class ObservationRow:
    """One indicator value on one day. The risk engine's input, verbatim."""

    subject_token: str
    indicator_code: str
    observed_on: date
    value: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "subject_token": self.subject_token,
            "indicator_code": self.indicator_code,
            "observed_on": self.observed_on.isoformat(),
            "value": self.value,
        }


@dataclass(frozen=True, slots=True)
class SubjectRow:
    subject_token: str
    unit_code: str
    sector_code: str
    region: str
    rank_band: str
    tenure_years: float
    tenure_bucket: str
    language: str
    enrolled: bool
    enrolled_on: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "subject_token": self.subject_token,
            "unit_code": self.unit_code,
            "sector_code": self.sector_code,
            "region": self.region,
            "rank_band": self.rank_band,
            "tenure_years": round(self.tenure_years, 2),
            "tenure_bucket": self.tenure_bucket,
            "language": self.language,
            "enrolled": self.enrolled,
            "enrolled_on": self.enrolled_on,
        }


@dataclass(frozen=True, slots=True)
class UnitRow:
    unit_code: str
    sector_code: str
    region: str
    posting_class: str
    family_station: bool
    assigned_strength: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "unit_code": self.unit_code,
            "sector_code": self.sector_code,
            "region": self.region,
            "posting_class": self.posting_class,
            "family_station": self.family_station,
            "assigned_strength": self.assigned_strength,
        }


@dataclass(frozen=True, slots=True)
class ConsentRow:
    """One subject's decision about one domain.

    Declines are written as rows with ``granted = false`` rather than omitted.
    An absent row and a refused row are different facts, and the coverage tests
    need to tell them apart.
    """

    subject_token: str
    domain: str
    channel: str
    granted: bool
    granted_on: str | None
    requires_opt_in: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "subject_token": self.subject_token,
            "domain": self.domain,
            "channel": self.channel,
            "granted": self.granted,
            "granted_on": self.granted_on,
            "requires_opt_in": self.requires_opt_in,
        }


@dataclass(frozen=True, slots=True)
class AcuteTriggerRow:
    subject_token: str
    kind: str
    occurred_at: datetime
    source: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "subject_token": self.subject_token,
            "kind": self.kind,
            "occurred_at": self.occurred_at.isoformat(),
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class IncidentRow:
    incident_id: str
    unit_code: str
    sector_code: str
    occurred_on: date
    kind: str
    severity: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "unit_code": self.unit_code,
            "sector_code": self.sector_code,
            "occurred_on": self.occurred_on.isoformat(),
            "kind": self.kind,
            "severity": round(self.severity, 4),
        }


@dataclass(frozen=True, slots=True)
class GroundTruthRow:
    """The injected answer, per subject. Never an input to any scoring path.

    ``deteriorating_at_end`` is the field that makes a false-negative count
    meaningful. A subject whose decline saturated a year before the window closed
    has a personal baseline that has moved with them and is invisible to SDD §4.5
    by construction; counting them as a miss would measure the method's
    definition rather than its performance.
    """

    subject_token: str
    cohort: str
    distressed: bool
    gaming: bool
    onset_day: int | None
    onset_on: str | None
    ramp_days: float
    severity: float
    strain_at_end: float
    deteriorating_at_end: bool
    acute: bool
    acute_on: str | None
    acute_kind: str | None
    acute_reported: bool
    enrolled: bool
    consented_domains: tuple[str, ...]
    rank_band: str
    sector_code: str
    unit_code: str
    tenure_bucket: str
    language: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "subject_token": self.subject_token,
            "cohort": self.cohort,
            "distressed": self.distressed,
            "gaming": self.gaming,
            "onset_day": self.onset_day,
            "onset_on": self.onset_on,
            "ramp_days": round(self.ramp_days, 2),
            "severity": round(self.severity, 4),
            "strain_at_end": round(self.strain_at_end, 4),
            "deteriorating_at_end": self.deteriorating_at_end,
            "acute": self.acute,
            "acute_on": self.acute_on,
            "acute_kind": self.acute_kind,
            "acute_reported": self.acute_reported,
            "enrolled": self.enrolled,
            "consented_domains": ",".join(sorted(self.consented_domains)),
            "rank_band": self.rank_band,
            "sector_code": self.sector_code,
            "unit_code": self.unit_code,
            "tenure_bucket": self.tenure_bucket,
            "language": self.language,
        }


def acute_timestamp(day: date, *, from_incident: bool) -> datetime:
    return at_ist(day, _INCIDENT_HOUR if from_incident else _ACUTE_HOUR)
