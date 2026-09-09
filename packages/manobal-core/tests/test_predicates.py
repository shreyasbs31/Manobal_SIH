"""The authorisation matrix (SDD §6.2, §6.3, §4.5, §4.6).

Pure unit tests — no database, no request, no server. Every predicate takes
facts and returns a decision, so the entire access-control surface can be
exercised exhaustively in milliseconds. That speed is the point: a control that
is expensive to test gets tested once.
"""

from __future__ import annotations

import pytest

from manobal_core.apps.authz.predicates import (
    DENY_FORCE,
    DENY_K_ANON,
    DENY_MFA,
    DENY_NO_GRANT,
    DENY_NOT_CONSENTED,
    DENY_ROLE,
    DENY_SELF_ONLY,
    DENY_TIER,
    DENY_UNCERTIFIED,
    DENY_UNIT,
    in_unit_scope,
    may_resolve_identity,
    may_view_aggregate,
    may_view_category_trend,
    may_view_flag,
    may_view_own_record,
    mfa_is_satisfied,
)
from manobal_core.apps.authz.principal import Principal
from manobal_core.apps.governance.enums import GrantScope, Role, Tier

BN = "CENTRAL/12BN"
COY = "CENTRAL/12BN/12BN_A"
SIBLING = "CENTRAL/12BN_RESERVE"

MFA_ROLES = ["welfare_officer", "commander", "medical_officer", "wdec_auditor"]
MFA_METHODS = ["otp", "mfa", "fido", "totp"]


def officer(**overrides: object) -> Principal:
    base = {
        "actor_id": "officer-001",
        "role": Role.WELFARE_OFFICER,
        "force_code": "CAPF",
        "unit_code": "12BN",
        "auth_methods": frozenset({"pwd", "otp"}),
    }
    return Principal(**{**base, **overrides})  # type: ignore[arg-type]


def flag_args(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "subject_force_code": "CAPF",
        "subject_unit_path": COY,
        "actor_unit_path": BN,
        "tier": Tier.T2,
        "officer_is_certified": True,
        "has_live_grant": True,
        "mfa_satisfied": True,
    }
    return {**base, **overrides}


class TestUnitScope:
    def test_a_unit_is_in_its_own_scope(self) -> None:
        assert in_unit_scope(actor_unit_path=BN, subject_unit_path=BN)

    def test_a_descendant_is_in_scope(self) -> None:
        assert in_unit_scope(actor_unit_path=BN, subject_unit_path=COY)

    def test_an_ancestor_is_not_in_scope(self) -> None:
        """A company commander does not thereby see the whole battalion."""
        assert not in_unit_scope(actor_unit_path=COY, subject_unit_path=BN)

    def test_a_prefix_sharing_sibling_is_not_in_scope(self) -> None:
        """The separator is what makes this correct.

        ``"CENTRAL/12BN_RESERVE".startswith("CENTRAL/12BN")`` is true, so a
        naive prefix test hands an officer a whole neighbouring formation. This
        is the single easiest way to silently widen access in the system.
        """
        assert not in_unit_scope(actor_unit_path=BN, subject_unit_path=SIBLING)

    def test_an_empty_path_is_never_in_scope(self) -> None:
        assert not in_unit_scope(actor_unit_path="", subject_unit_path=COY)
        assert not in_unit_scope(actor_unit_path=BN, subject_unit_path="")


class TestViewingAFlag:
    def test_a_certified_officer_with_a_grant_may_see_an_elevated_flag(self) -> None:
        assert may_view_flag(officer(), **flag_args())  # type: ignore[arg-type]

    @pytest.mark.parametrize("tier", [Tier.T0, Tier.T1])
    def test_low_tiers_are_never_visible_to_an_officer(self, tier: Tier) -> None:
        """§4.5. T0 tells nobody; T1 tells only the individual.

        This is what keeps the overwhelming majority of assessments from
        producing any officer interaction at all, and it holds regardless of how
        impeccable the officer's credentials are.
        """
        decision = may_view_flag(officer(), **flag_args(tier=tier))  # type: ignore[arg-type]
        assert not decision
        assert decision.reason == DENY_TIER

    @pytest.mark.parametrize("tier", [Tier.T2, Tier.T3, Tier.T4])
    def test_elevated_tiers_are_visible(self, tier: Tier) -> None:
        assert may_view_flag(officer(), **flag_args(tier=tier))  # type: ignore[arg-type]

    def test_an_officer_from_another_force_is_refused(self) -> None:
        decision = may_view_flag(officer(), **flag_args(subject_force_code="OTHER"))  # type: ignore[arg-type]
        assert decision.reason == DENY_FORCE

    def test_an_officer_outside_the_unit_subtree_is_refused(self) -> None:
        decision = may_view_flag(officer(), **flag_args(subject_unit_path=SIBLING))  # type: ignore[arg-type]
        assert decision.reason == DENY_UNIT

    def test_an_uncertified_officer_is_refused(self) -> None:
        """FR-4.6. An officer whose training lapsed receiving a T3 is a worse
        outcome than a slower response."""
        decision = may_view_flag(officer(), **flag_args(officer_is_certified=False))  # type: ignore[arg-type]
        assert decision.reason == DENY_UNCERTIFIED

    def test_a_role_alone_grants_nothing_without_a_live_grant(self) -> None:
        """The heart of the design: access is an event with an expiry, not a
        property of holding a job title."""
        decision = may_view_flag(officer(), **flag_args(has_live_grant=False))  # type: ignore[arg-type]
        assert decision.reason == DENY_NO_GRANT

    def test_a_commander_may_never_see_an_individual_flag(self) -> None:
        """§4.6. Commanders get aggregates. Never a person."""
        decision = may_view_flag(officer(role=Role.COMMANDER), **flag_args())  # type: ignore[arg-type]
        assert decision.reason == DENY_ROLE

    def test_personnel_cannot_use_the_officer_path(self) -> None:
        decision = may_view_flag(officer(role=Role.PERSONNEL), **flag_args())  # type: ignore[arg-type]
        assert decision.reason == DENY_ROLE

    def test_a_missing_second_factor_is_refused_before_anything_else(self) -> None:
        decision = may_view_flag(officer(), **flag_args(mfa_satisfied=False))  # type: ignore[arg-type]
        assert decision.reason == DENY_MFA


class TestViewingATrend:
    """FR-4.4. A category name is not a chart, and the difference is the
    individual's to decide."""

    def test_a_trend_needs_the_subjects_explicit_agreement(self) -> None:
        base = may_view_flag(officer(), **flag_args())  # type: ignore[arg-type]
        decision = may_view_category_trend(officer(), base=base, subject_granted_disclosure=False)
        assert decision.reason == DENY_NOT_CONSENTED

    def test_an_agreed_trend_is_visible(self) -> None:
        base = may_view_flag(officer(), **flag_args())  # type: ignore[arg-type]
        assert may_view_category_trend(officer(), base=base, subject_granted_disclosure=True)

    def test_agreement_cannot_widen_a_denied_base_decision(self) -> None:
        """Consent to share a trend does not override the tier gate. A person
        cannot volunteer themselves into an officer's queue at T1, and an
        officer cannot obtain visibility by asking nicely."""
        base = may_view_flag(officer(), **flag_args(tier=Tier.T1))  # type: ignore[arg-type]
        decision = may_view_category_trend(officer(), base=base, subject_granted_disclosure=True)
        assert not decision
        assert decision.reason == DENY_TIER


class TestResolvingIdentity:
    """§4.9. The narrowest gate in the system."""

    def test_a_flag_grant_does_not_imply_an_identity_grant(self) -> None:
        base = may_view_flag(officer(), **flag_args())  # type: ignore[arg-type]
        decision = may_resolve_identity(
            officer(), base=base, grant_scopes=[GrantScope.FLAG], mfa_satisfied=True
        )
        assert decision.reason == DENY_NO_GRANT

    def test_an_explicit_identity_scope_is_required_and_sufficient(self) -> None:
        base = may_view_flag(officer(), **flag_args())  # type: ignore[arg-type]
        assert may_resolve_identity(
            officer(),
            base=base,
            grant_scopes=[GrantScope.FLAG, GrantScope.IDENTITY],
            mfa_satisfied=True,
        )

    def test_identity_resolution_always_requires_a_second_factor(self) -> None:
        base = may_view_flag(officer(), **flag_args())  # type: ignore[arg-type]
        decision = may_resolve_identity(
            officer(), base=base, grant_scopes=[GrantScope.IDENTITY], mfa_satisfied=False
        )
        assert decision.reason == DENY_MFA


class TestSelfAccess:
    """FR-5.1. A person may always see their own record — and only their own."""

    def test_a_person_may_read_their_own_record(self) -> None:
        principal = Principal(
            actor_id="p1", role=Role.PERSONNEL, force_code="CAPF", subject_token="tok_me"
        )
        assert may_view_own_record(principal, subject_token="tok_me")

    def test_a_person_may_not_read_someone_elses(self) -> None:
        principal = Principal(
            actor_id="p1", role=Role.PERSONNEL, force_code="CAPF", subject_token="tok_me"
        )
        decision = may_view_own_record(principal, subject_token="tok_someone_else")
        assert decision.reason == DENY_SELF_ONLY

    def test_an_officer_cannot_borrow_the_self_access_path(self) -> None:
        decision = may_view_own_record(officer(), subject_token="tok_me")
        assert decision.reason == DENY_ROLE

    def test_a_personnel_principal_without_a_token_is_refused(self) -> None:
        principal = Principal(actor_id="p1", role=Role.PERSONNEL, force_code="CAPF")
        assert may_view_own_record(principal, subject_token="").reason == DENY_SELF_ONLY


class TestAggregates:
    """§4.6, §4.8. Commanders see shape, never people."""

    def commander(self) -> Principal:
        return Principal(
            actor_id="cmd-1",
            role=Role.COMMANDER,
            force_code="CAPF",
            unit_code="12BN",
            auth_methods=frozenset({"otp"}),
        )

    def test_a_sufficiently_large_cohort_is_visible(self) -> None:
        assert may_view_aggregate(
            self.commander(),
            actor_unit_path=BN,
            target_unit_path=COY,
            cohort_size=25,
            k_threshold=10,
        )

    def test_a_cohort_below_k_is_suppressed(self) -> None:
        decision = may_view_aggregate(
            self.commander(),
            actor_unit_path=BN,
            target_unit_path=COY,
            cohort_size=9,
            k_threshold=10,
        )
        assert decision.reason == DENY_K_ANON

    def test_suppression_is_unconditional_at_the_boundary(self) -> None:
        """Exactly k passes; k-1 does not. No rounding, no "fewer than ten"."""
        args = {"actor_unit_path": BN, "target_unit_path": COY, "k_threshold": 10}
        assert may_view_aggregate(self.commander(), cohort_size=10, **args)  # type: ignore[arg-type]
        assert not may_view_aggregate(self.commander(), cohort_size=9, **args)  # type: ignore[arg-type]

    def test_a_commander_cannot_query_outside_their_formation(self) -> None:
        decision = may_view_aggregate(
            self.commander(),
            actor_unit_path=BN,
            target_unit_path=SIBLING,
            cohort_size=100,
            k_threshold=10,
        )
        assert decision.reason == DENY_UNIT

    def test_an_officer_is_not_a_commander(self) -> None:
        decision = may_view_aggregate(
            officer(),
            actor_unit_path=BN,
            target_unit_path=COY,
            cohort_size=100,
            k_threshold=10,
        )
        assert decision.reason == DENY_ROLE


class TestSecondFactor:
    def test_an_officer_needs_a_second_factor(self) -> None:
        principal = officer(auth_methods=frozenset({"pwd"}))
        assert not mfa_is_satisfied(
            principal, required_roles=MFA_ROLES, accepted_methods=MFA_METHODS
        )

    def test_an_officer_with_otp_passes(self) -> None:
        assert mfa_is_satisfied(officer(), required_roles=MFA_ROLES, accepted_methods=MFA_METHODS)

    def test_personnel_are_not_forced_into_hardware_mfa(self) -> None:
        """Deliberate. Requiring a second factor of every constable would
        suppress enrolment far more than it would improve security, and a
        welfare system nobody joins helps nobody."""
        principal = Principal(
            actor_id="p1",
            role=Role.PERSONNEL,
            force_code="CAPF",
            auth_methods=frozenset({"pwd"}),
        )
        assert mfa_is_satisfied(principal, required_roles=MFA_ROLES, accepted_methods=MFA_METHODS)

    def test_an_unrecognised_amr_value_does_not_satisfy_the_requirement(self) -> None:
        principal = officer(auth_methods=frozenset({"handwave"}))
        assert not mfa_is_satisfied(
            principal, required_roles=MFA_ROLES, accepted_methods=MFA_METHODS
        )


class TestDecisionsCarryReasons:
    def test_a_denial_always_names_a_reason(self) -> None:
        """§7.3 needs the audit row to say *why* access was refused. "Denied"
        alone tells a later reviewer nothing about whether the control worked."""
        decision = may_view_flag(officer(), **flag_args(tier=Tier.T0))  # type: ignore[arg-type]
        assert not decision.allowed
        assert decision.reason and decision.reason != "ok"

    def test_a_decision_is_usable_as_a_boolean(self) -> None:
        assert bool(may_view_flag(officer(), **flag_args())) is True  # type: ignore[arg-type]
