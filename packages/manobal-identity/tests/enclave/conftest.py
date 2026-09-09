"""Fixtures for the Zone 3 enclave tests.

These tests run against a real ``iam_vault`` test database with a separate
settings module, because the whole point of the enclave is that it is a separate
Django project with one database and no route to the analytics plane. Testing it
under the Zone 2 settings would test something that does not exist.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from manobal_identity.apps.vault.models import DatabaseReplayGuard
from manobal_identity.apps.vault.services import (
    CallerContext,
    IdentityVault,
    PersonRecord,
)
from manobal_identity.crypto.kms import LocalKeyManagementService
from manobal_identity.grants.assertion import GrantAssertion, Operation, sign_assertion

KEY_ID = "core-test"
INGEST = CallerContext(
    workload_id="spiffe://manobal/ns/manobal-core/sa/ingest-worker",
    source_ip="10.20.0.5",
)
CASE_PATH = CallerContext(
    workload_id="spiffe://manobal/ns/manobal-core/sa/core-api", source_ip="10.20.0.9"
)


@pytest.fixture
def kms() -> LocalKeyManagementService:
    return LocalKeyManagementService(
        keks={1: b"\x11" * 32}, active_version=1, index_key=b"\x22" * 32
    )


@pytest.fixture
def signing_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


@pytest.fixture
def vault(kms, signing_key) -> IdentityVault:
    return IdentityVault(
        kms=kms,
        replay_guard=DatabaseReplayGuard(),
        trusted_keys={KEY_ID: signing_key.public_key()},
    )


@pytest.fixture
def people() -> list[PersonRecord]:
    """Three people in two units, one of them outside a 12BN officer's scope."""
    return [
        PersonRecord(
            service_no="CRPF-1987-114523",
            full_name="Havildar A. Kumar",
            rank_code="HAV",
            mobile_e164="+919812345670",
            unit_code="ALPHA-COY",
            unit_path="CENTRAL/WESTERN/12BN/ALPHA-COY",
            force_code="CRPF",
            enrolled_on=date(2019, 6, 1),
        ),
        PersonRecord(
            service_no="CRPF-1991-220914",
            full_name="Constable R. Devi",
            rank_code="CT",
            mobile_e164="+919812345671",
            unit_code="BRAVO-COY",
            unit_path="CENTRAL/WESTERN/12BN/BRAVO-COY",
            force_code="CRPF",
            enrolled_on=date(2021, 2, 14),
        ),
        PersonRecord(
            service_no="CRPF-1985-004417",
            full_name="Naik S. Rao",
            rank_code="NK",
            mobile_e164="+919812345672",
            unit_code="CHARLIE-COY",
            unit_path="CENTRAL/EASTERN/31BN/CHARLIE-COY",
            force_code="CRPF",
            enrolled_on=date(2015, 8, 30),
        ),
    ]


@pytest.fixture
def enrolled(vault: IdentityVault, people: list[PersonRecord]) -> dict[str, str]:
    """service_no -> subject_token for the fixture cohort."""
    return vault.tokenise(people, INGEST)


@pytest.fixture
def assert_for(signing_key: Ed25519PrivateKey):
    """Builds a signed grant assertion for a token, with sensible defaults."""

    def build(
        subject_token: str,
        *,
        operation: Operation = Operation.RESOLVE,
        actor_id: str = "officer_221",
        actor_unit_code: str = "12BN",
        assertion_id: str | None = None,
        second_approver_id: str | None = None,
        now: datetime | None = None,
    ) -> str:
        moment = now or datetime.now(UTC)
        return sign_assertion(
            GrantAssertion(
                assertion_id=assertion_id or f"asrt_{datetime.now(UTC).timestamp()}",
                key_id=KEY_ID,
                issuer="manobal-core",
                issued_at=moment,
                expires_at=moment + timedelta(minutes=2),
                operation=operation,
                grant_id="grant_9f2",
                grant_expires_at=moment + timedelta(hours=6),
                case_id="case_4471",
                subject_token=subject_token,
                purpose="welfare_contact",
                actor_id=actor_id,
                actor_role="welfare_officer",
                actor_unit_code=actor_unit_code,
                actor_force_code="CRPF",
                second_approver_id=second_approver_id,
            ),
            signing_key,
        )

    return build
