"""Capability assertions for identity resolution (SDD §4.9, §7.2, UC-11).

§4.9 requires that "every resolve requires an active, unexpired case grant with
a purpose code and an actor. There is no unscoped resolve." The enclave must
therefore satisfy itself that a grant exists — but it cannot query the
governance store to check, because a route from Zone 3 into Zone 2 is exactly
the route the zone model forbids.

So the grant travels with the request. Zone 2 signs a short-lived assertion
saying "grant G is live, officer O may resolve token T on case C for purpose P",
and the enclave verifies the signature. Zone 2 remains the authority on grants;
Zone 3 remains unable to reach back; and an officer cannot mint their own
permission, because they do not hold the signing key.

These tests are the enclave's threat model written down. Each one is an attack.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from manobal_identity.grants.assertion import (
    AssertionRejectedError,
    GrantAssertion,
    Operation,
    RejectionReason,
    sign_assertion,
    verify_assertion,
)
from manobal_identity.grants.replay import InMemoryReplayGuard

NOW = datetime(2026, 3, 14, 9, 30, tzinfo=UTC)
TOKEN = "st_7ytfnvqzk4c2mjxr6d8p3lwaeh5s9bug"


@pytest.fixture
def signing_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


@pytest.fixture
def trusted(signing_key: Ed25519PrivateKey) -> dict[str, object]:
    return {"core-2026-03": signing_key.public_key()}


@pytest.fixture
def replay() -> InMemoryReplayGuard:
    return InMemoryReplayGuard()


def make(**overrides: object) -> GrantAssertion:
    defaults: dict[str, object] = {
        "assertion_id": "asrt_01hxk3",
        "key_id": "core-2026-03",
        "issuer": "manobal-core",
        "issued_at": NOW,
        "expires_at": NOW + timedelta(seconds=120),
        "operation": Operation.RESOLVE,
        "grant_id": "grant_9f2",
        "grant_expires_at": NOW + timedelta(hours=6),
        "case_id": "case_4471",
        "subject_token": TOKEN,
        "purpose": "welfare_contact",
        "actor_id": "officer_221",
        "actor_role": "welfare_officer",
        "actor_unit_code": "BN-14",
        "actor_force_code": "CRPF",
        "second_approver_id": None,
    }
    return GrantAssertion(**(defaults | overrides))  # type: ignore[arg-type]


def check(
    assertion: GrantAssertion,
    signing_key: Ed25519PrivateKey,
    trusted: dict[str, object],
    replay: InMemoryReplayGuard,
    *,
    operation: Operation = Operation.RESOLVE,
    now: datetime = NOW,
) -> GrantAssertion:
    return verify_assertion(
        sign_assertion(assertion, signing_key),
        expecting=operation,
        trusted_keys=trusted,  # type: ignore[arg-type]
        replay_guard=replay,
        now=now,
    )


class TestTheHappyPath:
    def test_a_well_formed_assertion_verifies(
        self, signing_key, trusted, replay
    ) -> None:
        assert check(make(), signing_key, trusted, replay).subject_token == TOKEN

    def test_every_field_survives_the_round_trip(
        self, signing_key, trusted, replay
    ) -> None:
        original = make()
        assert check(original, signing_key, trusted, replay) == original


class TestForgery:
    def test_an_assertion_signed_by_an_unknown_key_is_refused(
        self, trusted, replay
    ) -> None:
        """An officer who mints their own permission holds no trusted key."""
        with pytest.raises(AssertionRejectedError) as caught:
            check(make(), Ed25519PrivateKey.generate(), trusted, replay)
        assert caught.value.reason is RejectionReason.BAD_SIGNATURE

    def test_an_assertion_naming_an_unknown_key_id_is_refused(
        self, signing_key, trusted, replay
    ) -> None:
        with pytest.raises(AssertionRejectedError) as caught:
            check(make(key_id="attacker-key"), signing_key, trusted, replay)
        assert caught.value.reason is RejectionReason.UNKNOWN_KEY

    def test_editing_the_payload_after_signing_is_detected(
        self, signing_key, trusted, replay
    ) -> None:
        """The classic attack: resolve a different person than the grant allows."""
        import base64
        import json

        signed = sign_assertion(make(), signing_key)
        prefix, payload_b64, signature = signed.split(".")
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=="))
        payload["subject_token"] = "st_someone_else"
        forged_payload = (
            base64.urlsafe_b64encode(json.dumps(payload).encode())
            .decode()
            .rstrip("=")
        )

        with pytest.raises(AssertionRejectedError) as caught:
            verify_assertion(
                f"{prefix}.{forged_payload}.{signature}",
                expecting=Operation.RESOLVE,
                trusted_keys=trusted,
                replay_guard=replay,
                now=NOW,
            )
        assert caught.value.reason is RejectionReason.BAD_SIGNATURE

    @pytest.mark.parametrize(
        "malformed",
        ["", "not-a-token", "mbga1.only-two", "mbga1..x", "wrong.b.c", "a.b.c.d"],
    )
    def test_a_malformed_assertion_is_refused_rather_than_crashing(
        self, malformed: str, trusted, replay
    ) -> None:
        with pytest.raises(AssertionRejectedError) as caught:
            verify_assertion(
                malformed,
                expecting=Operation.RESOLVE,
                trusted_keys=trusted,
                replay_guard=replay,
                now=NOW,
            )
        assert caught.value.reason is RejectionReason.MALFORMED


class TestExpiry:
    def test_an_expired_assertion_is_refused(
        self, signing_key, trusted, replay
    ) -> None:
        with pytest.raises(AssertionRejectedError) as caught:
            check(make(), signing_key, trusted, replay, now=NOW + timedelta(minutes=5))
        assert caught.value.reason is RejectionReason.ASSERTION_EXPIRED

    def test_an_assertion_from_the_future_is_refused(
        self, signing_key, trusted, replay
    ) -> None:
        with pytest.raises(AssertionRejectedError) as caught:
            check(make(), signing_key, trusted, replay, now=NOW - timedelta(minutes=5))
        assert caught.value.reason is RejectionReason.NOT_YET_VALID

    def test_small_clock_skew_between_zones_is_tolerated(
        self, signing_key, trusted, replay
    ) -> None:
        """Two hosts, two clocks. Refusing a T4 resolve over 3s of NTP drift
        would be a safety failure, not a security win."""
        assert check(
            make(), signing_key, trusted, replay, now=NOW - timedelta(seconds=3)
        )

    def test_an_assertion_may_not_outlive_its_grant(
        self, signing_key, trusted, replay
    ) -> None:
        """§4.9: the grant must be unexpired, not merely the assertion."""
        with pytest.raises(AssertionRejectedError) as caught:
            check(
                make(grant_expires_at=NOW - timedelta(minutes=1)),
                signing_key,
                trusted,
                replay,
            )
        assert caught.value.reason is RejectionReason.GRANT_EXPIRED

    def test_a_long_lived_assertion_is_refused(
        self, signing_key, trusted, replay
    ) -> None:
        """A capability valid for hours is a capability worth stealing."""
        with pytest.raises(AssertionRejectedError) as caught:
            check(
                make(expires_at=NOW + timedelta(hours=2)),
                signing_key,
                trusted,
                replay,
            )
        assert caught.value.reason is RejectionReason.LIFETIME_TOO_LONG


class TestReplay:
    def test_an_assertion_may_be_used_only_once(
        self, signing_key, trusted, replay
    ) -> None:
        """Otherwise a captured assertion resolves the same person repeatedly,
        and only the first resolution looks like it needed authorisation."""
        signed = sign_assertion(make(), signing_key)
        kwargs = {
            "expecting": Operation.RESOLVE,
            "trusted_keys": trusted,
            "replay_guard": replay,
            "now": NOW,
        }
        verify_assertion(signed, **kwargs)
        with pytest.raises(AssertionRejectedError) as caught:
            verify_assertion(signed, **kwargs)
        assert caught.value.reason is RejectionReason.REPLAYED

    def test_distinct_assertions_on_the_same_grant_are_both_accepted(
        self, signing_key, trusted, replay
    ) -> None:
        """One grant legitimately covers several resolutions over its life."""
        assert check(make(assertion_id="asrt_a"), signing_key, trusted, replay)
        assert check(make(assertion_id="asrt_b"), signing_key, trusted, replay)

    def test_a_rejected_assertion_does_not_consume_its_identifier(
        self, signing_key, trusted, replay
    ) -> None:
        """An attacker replaying a garbled assertion must not be able to burn
        the identifier of a legitimate one that has not arrived yet."""
        with pytest.raises(AssertionRejectedError):
            check(make(), Ed25519PrivateKey.generate(), trusted, replay)
        assert check(make(), signing_key, trusted, replay)


class TestDirectionalityAndOperation:
    def test_a_resolve_assertion_cannot_authorise_break_glass(
        self, signing_key, trusted, replay
    ) -> None:
        with pytest.raises(AssertionRejectedError) as caught:
            check(
                make(),
                signing_key,
                trusted,
                replay,
                operation=Operation.BREAK_GLASS,
            )
        assert caught.value.reason is RejectionReason.OPERATION_MISMATCH

    def test_a_break_glass_assertion_cannot_be_spent_on_a_routine_resolve(
        self, signing_key, trusted, replay
    ) -> None:
        """Break-glass is rate-limited far more tightly and alerts the WDEC.
        Spending one as an ordinary resolve would launder it past both."""
        with pytest.raises(AssertionRejectedError) as caught:
            check(
                make(
                    operation=Operation.BREAK_GLASS,
                    second_approver_id="officer_990",
                ),
                signing_key,
                trusted,
                replay,
                operation=Operation.RESOLVE,
            )
        assert caught.value.reason is RejectionReason.OPERATION_MISMATCH


class TestBreakGlassNeedsTwoPeople:
    """§4.9: break-glass requires typed justification plus second-person approval."""

    def test_break_glass_without_a_second_approver_is_refused(
        self, signing_key, trusted, replay
    ) -> None:
        with pytest.raises(AssertionRejectedError) as caught:
            check(
                make(operation=Operation.BREAK_GLASS),
                signing_key,
                trusted,
                replay,
                operation=Operation.BREAK_GLASS,
            )
        assert caught.value.reason is RejectionReason.SECOND_APPROVER_MISSING

    def test_an_officer_cannot_be_their_own_second_approver(
        self, signing_key, trusted, replay
    ) -> None:
        with pytest.raises(AssertionRejectedError) as caught:
            check(
                make(
                    operation=Operation.BREAK_GLASS,
                    actor_id="officer_221",
                    second_approver_id="officer_221",
                ),
                signing_key,
                trusted,
                replay,
                operation=Operation.BREAK_GLASS,
            )
        assert caught.value.reason is RejectionReason.SECOND_APPROVER_IS_ACTOR

    def test_break_glass_with_a_genuine_second_approver_is_accepted(
        self, signing_key, trusted, replay
    ) -> None:
        assert check(
            make(operation=Operation.BREAK_GLASS, second_approver_id="officer_990"),
            signing_key,
            trusted,
            replay,
            operation=Operation.BREAK_GLASS,
        )

    def test_a_routine_resolve_may_not_carry_a_second_approver(
        self, signing_key, trusted, replay
    ) -> None:
        """A second approver on an ordinary resolve means the caller has
        confused the two paths; refuse rather than guess which was meant."""
        with pytest.raises(AssertionRejectedError) as caught:
            check(make(second_approver_id="officer_990"), signing_key, trusted, replay)
        assert caught.value.reason is RejectionReason.UNEXPECTED_SECOND_APPROVER


class TestMandatoryContext:
    @pytest.mark.parametrize(
        "field",
        ["grant_id", "case_id", "purpose", "actor_id", "subject_token"],
    )
    def test_an_assertion_missing_required_context_is_refused(
        self, field: str, signing_key, trusted, replay
    ) -> None:
        """"There is no unscoped resolve" — every one of these is the scope."""
        with pytest.raises(AssertionRejectedError) as caught:
            check(make(**{field: ""}), signing_key, trusted, replay)
        assert caught.value.reason is RejectionReason.INCOMPLETE_CONTEXT

    def test_the_rejection_reason_is_always_machine_readable(
        self, signing_key, trusted, replay
    ) -> None:
        """Every refusal is audited, and audits are queried by reason."""
        with pytest.raises(AssertionRejectedError) as caught:
            check(make(purpose=""), signing_key, trusted, replay)
        assert isinstance(caught.value.reason, RejectionReason)
        assert caught.value.reason.value.startswith("MB-")


class TestTheAssertionCarriesNoIdentity:
    def test_an_assertion_never_carries_a_direct_identifier(
        self, signing_key
    ) -> None:
        """The assertion crosses Zone 2 → Zone 3 and is logged at both ends. If
        it carried a name or a service number, FR-2.4 would be broken by the
        very mechanism meant to protect it."""
        signed = sign_assertion(make(), signing_key)
        forbidden = {"service_no", "full_name", "mobile", "rank_code", "name"}
        assert not (forbidden & set(GrantAssertion.__dataclass_fields__))
        assert "service_no" not in signed
