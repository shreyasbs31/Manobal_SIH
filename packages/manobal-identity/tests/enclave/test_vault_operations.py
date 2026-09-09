"""End-to-end behaviour of the identity enclave (SDD §4.4, §4.9, §5.1, §5.4).

The unit suites cover the pieces. This one covers the claims the SDD actually
makes about the running service: that the vault holds ciphertext, that
tokenisation is one-directional and idempotent, that no resolution happens
without a live grant, that every crossing is recorded before it happens, and
that the record cannot afterwards be altered.
"""

from __future__ import annotations

import itertools
from datetime import UTC, datetime, timedelta

import pytest
from django.db import IntegrityError, connection

from manobal_identity.apps.vault.models import (
    CHAIN_GENESIS,
    Direction,
    ResolutionAudit,
    SubjectIdentity,
)
from manobal_identity.apps.vault.services import ResolutionDeniedError, SubjectNotFoundError
from manobal_identity.grants.assertion import AssertionRejectedError, Operation
from manobal_identity.policy.resolution import (
    BREAK_GLASS_PER_DAY,
    RESOLVE_PER_HOUR,
    Anomaly,
)

from .conftest import CASE_PATH, INGEST

pytestmark = pytest.mark.django_db

KUMAR = "CRPF-1987-114523"
RAO = "CRPF-1985-004417"


class TestTokenisation:
    def test_every_person_receives_a_token(self, enrolled, people) -> None:
        assert set(enrolled) == {p.service_no for p in people}
        assert all(t.startswith("st_") for t in enrolled.values())

    def test_different_people_receive_different_tokens(self, enrolled) -> None:
        assert len(set(enrolled.values())) == len(enrolled)

    def test_tokenising_the_same_person_twice_returns_the_same_token(
        self, vault, people, enrolled
    ) -> None:
        """The nightly HRMS delta re-sends people who are already enrolled. A
        second token would split one person's history into two half-baselines,
        neither of which would ever establish."""
        assert vault.tokenise(people, INGEST) == enrolled

    def test_re_tokenising_does_not_create_duplicate_vault_rows(
        self, vault, people, enrolled
    ) -> None:
        vault.tokenise(people, INGEST)
        assert SubjectIdentity.objects.count() == len(people)

    def test_a_service_number_written_differently_maps_to_the_same_token(
        self, vault, people, enrolled
    ) -> None:
        variant = [
            type(people[0])(**{**vars_of(people[0]), "service_no": "crpf 1987 114523"})
        ]
        assert vault.tokenise(variant, INGEST)["crpf 1987 114523"] == enrolled[KUMAR]

    def test_tokenise_returns_tokens_and_nothing_else(self, enrolled, people) -> None:
        """§4.4: the write direction may not answer the read question. The
        return value is checked here; that it *cannot* is structural — the
        method has no code path that decrypts."""
        rendered = repr(enrolled)
        for person in people:
            assert person.full_name not in rendered
            assert person.mobile_e164 not in rendered


class TestTheVaultHoldsCiphertext:
    """NFR-SEC2: a stolen dump, on its own, must be ciphertext."""

    def test_no_identifying_plaintext_is_stored(self, enrolled, people) -> None:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM subject_identity")
            dump = repr(cursor.fetchall())
        for person in people:
            for secret in (
                person.service_no,
                person.full_name,
                person.rank_code,
                person.mobile_e164,
            ):
                assert secret not in dump

    def test_the_blind_index_does_not_reveal_the_service_number(
        self, enrolled
    ) -> None:
        indexes = SubjectIdentity.objects.values_list("service_no_index", flat=True)
        assert all("114523" not in index for index in indexes)

    def test_the_unit_is_stored_in_the_clear_on_purpose(self, enrolled) -> None:
        """Organisational, not identifying — and the out-of-unit anomaly check
        in §4.9 cannot run without it."""
        row = SubjectIdentity.objects.get(subject_token=enrolled[KUMAR])
        assert row.current_unit_path == "CENTRAL/WESTERN/12BN/ALPHA-COY"

    def test_a_row_renders_as_its_token_not_as_a_person(self, enrolled) -> None:
        row = SubjectIdentity.objects.get(subject_token=enrolled[KUMAR])
        assert str(row) == enrolled[KUMAR]


class TestResolution:
    def test_an_authorised_resolution_returns_the_person(
        self, vault, enrolled, assert_for
    ) -> None:
        identity = vault.resolve(
            assert_for(enrolled[KUMAR]),
            operation=Operation.RESOLVE,
            caller=CASE_PATH,
        )
        assert identity.service_no == KUMAR
        assert identity.full_name == "Havildar A. Kumar"
        assert identity.mobile_e164 == "+919812345670"

    def test_resolution_without_a_grant_assertion_is_impossible(
        self, vault, enrolled
    ) -> None:
        """There is no argument combination that resolves without one."""
        with pytest.raises(AssertionRejectedError):
            vault.resolve("", operation=Operation.RESOLVE, caller=CASE_PATH)

    def test_a_forged_assertion_resolves_nothing(self, vault, enrolled) -> None:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
        )

        from manobal_identity.grants.assertion import GrantAssertion, sign_assertion

        now = datetime.now(UTC)
        forged = sign_assertion(
            GrantAssertion(
                assertion_id="asrt_forged",
                key_id="core-test",
                issuer="manobal-core",
                issued_at=now,
                expires_at=now + timedelta(minutes=1),
                operation=Operation.RESOLVE,
                grant_id="g",
                grant_expires_at=now + timedelta(hours=1),
                case_id="c",
                subject_token=enrolled[KUMAR],
                purpose="welfare_contact",
                actor_id="attacker",
                actor_role="welfare_officer",
                actor_unit_code="12BN",
                actor_force_code="CRPF",
            ),
            Ed25519PrivateKey.generate(),
        )
        with pytest.raises(AssertionRejectedError):
            vault.resolve(forged, operation=Operation.RESOLVE, caller=CASE_PATH)

    def test_an_unknown_token_is_refused_and_audited(
        self, vault, enrolled, assert_for
    ) -> None:
        with pytest.raises(SubjectNotFoundError):
            vault.resolve(
                assert_for("st_nobody"),
                operation=Operation.RESOLVE,
                caller=CASE_PATH,
            )
        assert ResolutionAudit.objects.filter(granted=False).exists()

    def test_a_resolution_may_not_be_replayed(
        self, vault, enrolled, assert_for
    ) -> None:
        signed = assert_for(enrolled[KUMAR], assertion_id="asrt_once")
        vault.resolve(signed, operation=Operation.RESOLVE, caller=CASE_PATH)
        with pytest.raises(AssertionRejectedError):
            vault.resolve(signed, operation=Operation.RESOLVE, caller=CASE_PATH)


class TestRateLimitsBite:
    def test_the_sixth_resolution_in_an_hour_is_refused(
        self, vault, enrolled, assert_for
    ) -> None:
        for n in range(RESOLVE_PER_HOUR):
            vault.resolve(
                assert_for(enrolled[KUMAR], assertion_id=f"asrt_{n}"),
                operation=Operation.RESOLVE,
                caller=CASE_PATH,
            )
        with pytest.raises(ResolutionDeniedError) as caught:
            vault.resolve(
                assert_for(enrolled[KUMAR], assertion_id="asrt_over"),
                operation=Operation.RESOLVE,
                caller=CASE_PATH,
            )
        assert caught.value.reason == "MB-3201"

    def test_the_limit_is_per_officer_not_global(
        self, vault, enrolled, assert_for
    ) -> None:
        """One officer exhausting their quota must not lock out a colleague
        who is dealing with a different case."""
        for n in range(RESOLVE_PER_HOUR):
            vault.resolve(
                assert_for(enrolled[KUMAR], assertion_id=f"asrt_a{n}"),
                operation=Operation.RESOLVE,
                caller=CASE_PATH,
            )
        assert vault.resolve(
            assert_for(
                enrolled[KUMAR], actor_id="officer_444", assertion_id="asrt_b0"
            ),
            operation=Operation.RESOLVE,
            caller=CASE_PATH,
        )

    def test_a_refused_resolution_does_not_consume_quota(
        self, vault, enrolled, assert_for
    ) -> None:
        """Otherwise a caller could exhaust an officer's quota with requests
        that were never going to succeed."""
        for n in range(20):
            with pytest.raises(SubjectNotFoundError):
                vault.resolve(
                    assert_for("st_nobody", assertion_id=f"asrt_miss{n}"),
                    operation=Operation.RESOLVE,
                    caller=CASE_PATH,
                )
        assert vault.resolve(
            assert_for(enrolled[KUMAR], assertion_id="asrt_real"),
            operation=Operation.RESOLVE,
            caller=CASE_PATH,
        )


class TestBreakGlass:
    def test_break_glass_reaches_the_person_when_routine_quota_is_spent(
        self, vault, enrolled, assert_for
    ) -> None:
        """The T4 acute case at the end of a busy shift. If the emergency path
        inherited the routine limit, this is the call that would fail."""
        for n in range(RESOLVE_PER_HOUR):
            vault.resolve(
                assert_for(enrolled[KUMAR], assertion_id=f"asrt_{n}"),
                operation=Operation.RESOLVE,
                caller=CASE_PATH,
            )
        identity = vault.resolve(
            assert_for(
                enrolled[KUMAR],
                operation=Operation.BREAK_GLASS,
                second_approver_id="officer_990",
                assertion_id="asrt_bg",
            ),
            operation=Operation.BREAK_GLASS,
            caller=CASE_PATH,
        )
        assert identity.service_no == KUMAR

    def test_break_glass_is_capped_at_two_a_day(
        self, vault, enrolled, assert_for
    ) -> None:
        for n in range(BREAK_GLASS_PER_DAY):
            vault.resolve(
                assert_for(
                    enrolled[KUMAR],
                    operation=Operation.BREAK_GLASS,
                    second_approver_id="officer_990",
                    assertion_id=f"asrt_bg{n}",
                ),
                operation=Operation.BREAK_GLASS,
                caller=CASE_PATH,
            )
        with pytest.raises(ResolutionDeniedError) as caught:
            vault.resolve(
                assert_for(
                    enrolled[KUMAR],
                    operation=Operation.BREAK_GLASS,
                    second_approver_id="officer_990",
                    assertion_id="asrt_bg_over",
                ),
                operation=Operation.BREAK_GLASS,
                caller=CASE_PATH,
            )
        assert caught.value.reason == "MB-3203"

    def test_break_glass_is_recorded_under_its_own_direction(
        self, vault, enrolled, assert_for
    ) -> None:
        """§4.9 gives break-glass its own audit category, so the WDEC can count
        emergencies without filtering them out of routine traffic by hand."""
        vault.resolve(
            assert_for(
                enrolled[KUMAR],
                operation=Operation.BREAK_GLASS,
                second_approver_id="officer_990",
                assertion_id="asrt_bg",
            ),
            operation=Operation.BREAK_GLASS,
            caller=CASE_PATH,
        )
        assert ResolutionAudit.objects.filter(
            direction=Direction.BREAK_GLASS
        ).exists()


class TestOutOfUnitDetection:
    def test_resolving_outside_the_officers_unit_is_recorded_as_an_anomaly(
        self, vault, enrolled, assert_for
    ) -> None:
        vault.resolve(
            assert_for(enrolled[RAO], actor_unit_code="12BN"),
            operation=Operation.RESOLVE,
            caller=CASE_PATH,
        )
        entry = ResolutionAudit.objects.latest("seq")
        assert Anomaly.OUT_OF_UNIT.value in entry.anomalies

    def test_the_enclave_checks_the_unit_itself_rather_than_trusting_the_caller(
        self, vault, enrolled, assert_for
    ) -> None:
        """Zone 2 already checks scope. This is the independent check: the
        enclave compares against the vault's own record of where the subject is
        posted, so a compromised Zone 2 asserting a convenient unit is still
        caught."""
        vault.resolve(
            assert_for(enrolled[RAO], actor_unit_code="31BN"),
            operation=Operation.RESOLVE,
            caller=CASE_PATH,
        )
        entry = ResolutionAudit.objects.latest("seq")
        assert Anomaly.OUT_OF_UNIT.value not in entry.anomalies


class TestEveryCrossingIsAudited:
    def test_a_tokenise_batch_is_one_audit_entry_with_a_count(
        self, enrolled, people
    ) -> None:
        """Eighty thousand entries for a nightly delta would bury the resolve
        entries that actually need reading."""
        entry = ResolutionAudit.objects.get(direction=Direction.TOKENISE)
        assert entry.record_count == len(people)

    def test_a_successful_resolution_is_audited(
        self, vault, enrolled, assert_for
    ) -> None:
        vault.resolve(
            assert_for(enrolled[KUMAR]),
            operation=Operation.RESOLVE,
            caller=CASE_PATH,
        )
        entry = ResolutionAudit.objects.filter(direction=Direction.RESOLVE).latest("seq")
        assert entry.granted
        assert entry.actor_id == "officer_221"
        assert entry.case_id == "case_4471"
        assert entry.purpose_code == "welfare_contact"

    def test_a_refused_resolution_is_audited_too(
        self, vault, enrolled, assert_for
    ) -> None:
        for n in range(RESOLVE_PER_HOUR):
            vault.resolve(
                assert_for(enrolled[KUMAR], assertion_id=f"asrt_{n}"),
                operation=Operation.RESOLVE,
                caller=CASE_PATH,
            )
        with pytest.raises(ResolutionDeniedError):
            vault.resolve(
                assert_for(enrolled[KUMAR], assertion_id="asrt_over"),
                operation=Operation.RESOLVE,
                caller=CASE_PATH,
            )
        assert ResolutionAudit.objects.filter(
            direction=Direction.RESOLVE, granted=False, denial_reason="MB-3201"
        ).exists()

    def test_the_audit_never_records_the_identity_it_disclosed(
        self, vault, enrolled, assert_for
    ) -> None:
        """The audit says a resolution happened, who did it and why. Recording
        the answer would turn the audit log into a second, less guarded copy of
        the vault."""
        vault.resolve(
            assert_for(enrolled[KUMAR]),
            operation=Operation.RESOLVE,
            caller=CASE_PATH,
        )
        rendered = repr(list(ResolutionAudit.objects.values()))
        assert "Havildar A. Kumar" not in rendered
        assert KUMAR not in rendered
        assert "+919812345670" not in rendered


class TestTheAuditIsTamperEvident:
    def test_the_chain_starts_at_genesis(self, enrolled) -> None:
        assert ResolutionAudit.objects.earliest("seq").prev_hash == CHAIN_GENESIS

    def test_each_entry_chains_to_its_predecessor(
        self, vault, enrolled, assert_for
    ) -> None:
        for n in range(3):
            vault.resolve(
                assert_for(enrolled[KUMAR], assertion_id=f"asrt_{n}"),
                operation=Operation.RESOLVE,
                caller=CASE_PATH,
            )
        entries = list(ResolutionAudit.objects.order_by("seq"))
        for previous, current in itertools.pairwise(entries):
            assert current.prev_hash == previous.entry_hash

    def test_the_database_refuses_to_update_an_entry(self, enrolled) -> None:
        with pytest.raises(IntegrityError), connection.cursor() as cursor:
            cursor.execute(
                "UPDATE resolution_audit SET actor_id = 'somebody_else'"
            )

    def test_the_database_refuses_to_delete_an_entry(self, enrolled) -> None:
        with pytest.raises(IntegrityError), connection.cursor() as cursor:
            cursor.execute("DELETE FROM resolution_audit")

    def test_the_orm_refuses_to_rewrite_an_entry(self, enrolled) -> None:
        entry = ResolutionAudit.objects.earliest("seq")
        entry.actor_id = "somebody_else"
        with pytest.raises(IntegrityError):
            entry.save()

    def test_the_chain_verifier_reports_an_intact_chain(
        self, vault, enrolled, assert_for
    ) -> None:
        vault.resolve(
            assert_for(enrolled[KUMAR]),
            operation=Operation.RESOLVE,
            caller=CASE_PATH,
        )
        with connection.cursor() as cursor:
            cursor.execute("SELECT manobal_identity_audit_chain_break()")
            assert cursor.fetchone()[0] is None


class TestTheEnclaveHasNoRouteOut:
    def test_the_enclave_is_configured_with_exactly_one_database(self) -> None:
        """§3.2: analytics has no route to identity, and identity has none
        back. A second alias here would be that route."""
        from django.conf import settings

        assert set(settings.DATABASES) == {"default"}
        assert settings.DATABASES["default"]["NAME"].startswith("test_") or settings.DATABASES[
            "default"
        ]["NAME"] == "iam_vault"

    def test_the_enclave_does_not_import_the_analytics_service(self) -> None:
        """Sharing a helper would put manobal_core — and with it the analytics
        database configuration — inside the enclave's image."""
        import pathlib

        root = pathlib.Path(__file__).resolve().parents[3] / "src" / "manobal_identity"
        offenders = [
            path.relative_to(root)
            for path in root.rglob("*.py")
            if "manobal_core" in path.read_text()
        ]
        assert offenders == []


def vars_of(record) -> dict:
    """Field values of a slotted dataclass."""
    import dataclasses

    return {f.name: getattr(record, f.name) for f in dataclasses.fields(record)}
