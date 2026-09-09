"""Rate limits and anomaly detection for identity resolution (SDD §4.9, §7.2).

Pure decision logic: it takes a tally and some context and returns a verdict.
Counting is somebody else's job, and keeping it that way is what makes the
policy testable at every boundary condition without a database.

Two things are decided here, and they are independent:

``allowed``
    Whether the resolution proceeds. Governed by the published limits in §7.2.

``anomalies`` / ``notify_wdec`` / ``flag_session``
    What the Welfare Data Ethics Committee is told. A refusal is always
    reported — a blocked bulk de-anonymisation attempt is the most interesting
    event this service can emit, and it must not be quieter than a successful
    resolution. Some permitted resolutions are reported too.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from manobal_identity.grants.assertion import Operation

RESOLVE_PER_HOUR: Final = 5
RESOLVE_PER_DAY: Final = 20
BREAK_GLASS_PER_DAY: Final = 2
"""The limits published in SDD §7.2. Officers are told these numbers, so they
are governance commitments rather than tuning knobs — changing one is a document
change first and a code change second."""


class DenialReason(StrEnum):
    """Why a resolution was refused."""

    HOURLY_LIMIT = "MB-3201"
    DAILY_LIMIT = "MB-3202"
    BREAK_GLASS_LIMIT = "MB-3203"


class Anomaly(StrEnum):
    """What the WDEC is told about."""

    RATE_LIMIT_BREACHED = "MB-3301"
    OUT_OF_UNIT = "MB-3302"
    BREAK_GLASS_USED = "MB-3303"


@dataclass(frozen=True, slots=True)
class ResolutionCounts:
    """What this officer has already done, over the two published windows."""

    resolves_last_hour: int
    resolves_last_day: int
    break_glass_last_day: int


@dataclass(frozen=True, slots=True)
class PolicyOutcome:
    allowed: bool
    denial: DenialReason | None
    anomalies: tuple[Anomaly, ...]
    notify_wdec: bool
    flag_session: bool


def evaluate_resolution(
    *,
    operation: Operation,
    counts: ResolutionCounts,
    actor_unit_code: str,
    subject_unit_path: str,
) -> PolicyOutcome:
    """Decide whether a resolution proceeds and what the WDEC should hear."""
    anomalies: list[Anomaly] = []
    denial: DenialReason | None = None
    flag_session = False

    if not _within_scope(actor_unit_code, subject_unit_path):
        # Permitted, but always visible. An officer covering a neighbouring
        # sub-unit during a transfer has a real reason to be here; so does
        # somebody fishing. The enclave cannot tell them apart, and it is the
        # only component that could notice at all — it alone holds the
        # subject's true unit rather than the caller's claim about it.
        anomalies.append(Anomaly.OUT_OF_UNIT)

    if operation is Operation.BREAK_GLASS:
        anomalies.append(Anomaly.BREAK_GLASS_USED)
        if counts.break_glass_last_day >= BREAK_GLASS_PER_DAY:
            denial = DenialReason.BREAK_GLASS_LIMIT
            flag_session = True
    elif counts.resolves_last_hour >= RESOLVE_PER_HOUR:
        denial = DenialReason.HOURLY_LIMIT
    elif counts.resolves_last_day >= RESOLVE_PER_DAY:
        denial = DenialReason.DAILY_LIMIT

    if denial in (DenialReason.HOURLY_LIMIT, DenialReason.DAILY_LIMIT):
        anomalies.append(Anomaly.RATE_LIMIT_BREACHED)
        flag_session = True

    return PolicyOutcome(
        allowed=denial is None,
        denial=denial,
        anomalies=tuple(anomalies),
        notify_wdec=bool(anomalies),
        flag_session=flag_session,
    )


def _within_scope(actor_unit_code: str, subject_unit_path: str) -> bool:
    """Is the subject inside the officer's unit or one of its sub-units?

    Compares whole path segments rather than substrings. ``"12BN" in path``
    would match ``"CENTRAL/WESTERN/12BN-DET/ALPHA"``, quietly granting an
    officer scope over a detachment that is not theirs — the kind of bug that
    never announces itself.

    An empty path fails closed. Not knowing where somebody is posted is not
    evidence that they are in front of you.
    """
    if not subject_unit_path or not actor_unit_code:
        return False
    return actor_unit_code in subject_unit_path.split("/")
