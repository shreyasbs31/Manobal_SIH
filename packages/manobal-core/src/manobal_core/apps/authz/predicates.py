"""Access predicates: role-based and attribute-based, evaluated per request.

SDD §6.2 and §6.3.

Holding a role is necessary and never sufficient. Every individual-level access
must satisfy *all* of:

* the role may perform this kind of access at all (RBAC);
* the person is inside the actor's organisational scope (ABAC);
* the assessment is officer-visible — T0 and T1 never are (§4.5);
* a live, unexpired, unrevoked grant exists for this actor, this person and this
  scope (§5.2 ACCESS_GRANT);
* where the role requires it, a second factor was actually used (NFR-SEC3).

Two properties of this module are deliberate. First, it is **pure**: predicates
take already-loaded facts and return a decision, with no database access and no
request object, so the whole authorisation surface is unit-testable without a
server. Second, every denial carries a **reason code**, because the audit log
must record *why* access was refused; "denied" alone tells a later reviewer
nothing about whether the control worked as intended.

The functions return a :class:`Decision` rather than a bool. A bare bool invites
``if not allowed`` at a call site that forgets to write the audit row; a
Decision carries the reason that the audit row needs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from ..governance.enums import (
    MEDICAL_OFFICER_TIERS,
    OFFICER_VISIBLE_TIERS,
    GrantScope,
    Role,
    Tier,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .principal import Principal


@dataclass(frozen=True, slots=True)
class Decision:
    """The outcome of an authorisation check, with a machine-readable reason."""

    allowed: bool
    reason: str

    def __bool__(self) -> bool:
        return self.allowed


ALLOW: Final = Decision(True, "ok")

# Reason codes. Stable strings, because they end up in audit rows that are read
# years later and in error responses that support staff triage from.
DENY_ROLE: Final = "role_not_permitted"
DENY_FORCE: Final = "outside_force"
DENY_UNIT: Final = "outside_unit_scope"
DENY_TIER: Final = "tier_not_officer_visible"
DENY_NO_GRANT: Final = "no_live_access_grant"
DENY_MFA: Final = "second_factor_required"
DENY_UNCERTIFIED: Final = "officer_training_expired"
DENY_SELF_ONLY: Final = "personnel_may_access_only_own_record"
DENY_K_ANON: Final = "cohort_below_k_threshold"
DENY_NOT_CONSENTED: Final = "subject_has_not_consented_to_disclosure"


def in_unit_scope(*, actor_unit_path: str, subject_unit_path: str) -> bool:
    """True when the subject's unit is the actor's unit or beneath it.

    A prefix test on the materialised path, with the separator included so that
    ``12BN`` does not match ``12BN_RESERVE``. That off-by-one is exactly the kind
    of mistake that silently widens an officer's reach across a whole formation.
    """
    if not actor_unit_path or not subject_unit_path:
        return False
    return subject_unit_path == actor_unit_path or subject_unit_path.startswith(
        f"{actor_unit_path}/"
    )


def may_view_flag(
    principal: Principal,
    *,
    subject_force_code: str,
    subject_unit_path: str,
    actor_unit_path: str,
    tier: Tier,
    officer_is_certified: bool,
    has_live_grant: bool,
    mfa_satisfied: bool,
) -> Decision:
    """May this actor see that this person is flagged, and in which categories?

    Checks are ordered cheapest-and-broadest first, which also means a denial
    reports the most fundamental failure rather than an incidental one. An
    officer from the wrong force should be told they are outside the force, not
    that their training has lapsed.
    """
    if principal.role not in {Role.WELFARE_OFFICER, Role.MEDICAL_OFFICER}:
        return Decision(False, DENY_ROLE)
    if not mfa_satisfied:
        return Decision(False, DENY_MFA)
    if principal.force_code != subject_force_code:
        return Decision(False, DENY_FORCE)
    if not in_unit_scope(actor_unit_path=actor_unit_path, subject_unit_path=subject_unit_path):
        return Decision(False, DENY_UNIT)
    if tier not in OFFICER_VISIBLE_TIERS:
        # The single most consequential line in this module. T1 exists precisely
        # so that a mild, uncorroborated drift is surfaced to the individual and
        # to nobody else, and the majority of assessments never reach an officer.
        return Decision(False, DENY_TIER)
    if principal.role is Role.MEDICAL_OFFICER and tier not in MEDICAL_OFFICER_TIERS:
        # §1.4 makes the medical officer an *escalation target*, not a second
        # reviewer of the routine queue. A T2 case is a welfare conversation;
        # routing it to a clinician both medicalises ordinary distress and
        # widens the circle of people who know, which is the specific harm
        # §7.7 is written to prevent.
        return Decision(False, DENY_TIER)
    if not officer_is_certified:
        return Decision(False, DENY_UNCERTIFIED)
    if not has_live_grant:
        return Decision(False, DENY_NO_GRANT)
    return ALLOW


def may_view_category_trend(
    principal: Principal,
    *,
    base: Decision,
    subject_granted_disclosure: bool,
) -> Decision:
    """May this actor see the *chart* behind a category, not merely its name?

    Strictly narrower than :func:`may_view_flag`. A flag says "sleep and
    recovery"; a trend shows the shape of someone's nights for three months.
    FR-4.4 makes the second one the individual's decision, and an unanswered
    request grants nothing.
    """
    if not base.allowed:
        return base
    if not subject_granted_disclosure:
        return Decision(False, DENY_NOT_CONSENTED)
    return ALLOW


def may_resolve_identity(
    principal: Principal,
    *,
    base: Decision,
    grant_scopes: Iterable[GrantScope],
    mfa_satisfied: bool,
) -> Decision:
    """May this actor turn a token back into a person? (§4.9)

    The narrowest gate in the system. It additionally requires a grant whose
    scope is explicitly ``IDENTITY``: a grant to view a flag does not imply
    permission to learn who the flag is about, because for most welfare actions —
    counting, trending, reviewing thresholds — nobody needs to know.

    Note that this predicate authorises only the *request*. The resolution itself
    happens in Zone 3, which enforces its own scope check independently. Neither
    side trusts the other's decision.
    """
    if not base.allowed:
        return base
    if not mfa_satisfied:
        return Decision(False, DENY_MFA)
    if GrantScope.IDENTITY not in set(grant_scopes):
        return Decision(False, DENY_NO_GRANT)
    return ALLOW


def may_view_own_record(principal: Principal, *, subject_token: str) -> Decision:
    """FR-5.1. A person may always see their own data, and only their own.

    No grant is required and no officer approval is involved: this is the
    individual exercising a right, not an officer being permitted an access.
    """
    if not principal.is_personnel:
        return Decision(False, DENY_ROLE)
    if not principal.subject_token or principal.subject_token != subject_token:
        return Decision(False, DENY_SELF_ONLY)
    return ALLOW


def may_view_aggregate(
    principal: Principal,
    *,
    actor_unit_path: str,
    target_unit_path: str,
    cohort_size: int,
    k_threshold: int,
) -> Decision:
    """May a commander see this unit-level rollup? (§4.6, §4.8)

    A commander gets aggregates and nothing else — never a name, never a token,
    never an individual tier. That separation is what keeps the system a welfare
    instrument rather than a management one, and it is why :class:`Principal` for
    a commander is never paired with a subject token anywhere in this codebase.

    Suppression below *k* is unconditional and not roundable. Reporting "fewer
    than ten" for a unit of eight still tells a commander something about eight
    identifiable people.
    """
    if principal.role is not Role.COMMANDER:
        return Decision(False, DENY_ROLE)
    if not in_unit_scope(actor_unit_path=actor_unit_path, subject_unit_path=target_unit_path):
        return Decision(False, DENY_UNIT)
    if cohort_size < k_threshold:
        return Decision(False, DENY_K_ANON)
    return ALLOW


def mfa_is_satisfied(
    principal: Principal, *, required_roles: Iterable[str], accepted_methods: Iterable[str]
) -> bool:
    """Did the token actually evidence a second factor, where one is required?

    Reads ``amr`` rather than trusting a boolean claim, because ``amr`` states
    what the identity provider observed. A role outside ``required_roles`` — in
    practice, personnel on their own record — passes without one, since forcing
    hardware MFA on every constable would suppress enrolment far more than it
    would improve security.
    """
    if principal.role.value not in set(required_roles):
        return True
    return bool(principal.auth_methods & {m.lower() for m in accepted_methods})
