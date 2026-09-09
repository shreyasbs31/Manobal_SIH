"""Shared fixtures for the core service test suite."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from manobal_core.apps.authz.principal import Principal
from manobal_core.apps.governance.enums import (
    DeviceTier,
    LegalBasis,
    PurposeCode,
    Role,
)
from manobal_core.apps.governance.models import (
    ConsentTextVersion,
    OfficerProfile,
    Subject,
    Unit,
)

#: The five analytics stores. A test that spans stores must name them, which
#: makes any cross-store access an explicit, reviewable decision in the test
#: itself rather than something that happens by default.
ALL_STORES = ("default", "org", "psy", "bio", "voice")


@pytest.fixture
def unit_tree(db: None) -> dict[str, Unit]:
    """A three-level formation: force -> battalion -> company.

    Depth matters for the scope predicate tests. A single flat unit would let a
    broken prefix match pass, since everything would trivially be in scope.
    """
    del db
    force = Unit.objects.create(
        code="CENTRAL", name="Central Force", force_code="CAPF", depth=0, path="CENTRAL"
    )
    battalion = Unit.objects.create(
        code="12BN",
        name="12 Battalion",
        force_code="CAPF",
        parent=force,
        depth=1,
        path="CENTRAL/12BN",
    )
    company = Unit.objects.create(
        code="12BN_A",
        name="A Company",
        force_code="CAPF",
        parent=battalion,
        depth=2,
        path="CENTRAL/12BN/12BN_A",
    )
    # A sibling that must never fall inside 12BN's scope. Its code shares a
    # prefix with 12BN precisely to catch a separator-less startswith().
    sibling = Unit.objects.create(
        code="12BN_RESERVE",
        name="12 Battalion Reserve",
        force_code="CAPF",
        parent=force,
        depth=1,
        path="CENTRAL/12BN_RESERVE",
    )
    return {"force": force, "battalion": battalion, "company": company, "sibling": sibling}


@pytest.fixture
def subject(unit_tree: dict[str, Unit]) -> Subject:
    return Subject.objects.create(
        subject_token="tok_subject_0001",
        unit=unit_tree["company"],
        force_code="CAPF",
        rank_band="constable",
        service_years_bucket="5-9",
        enrolled_at=timezone.now(),
        baseline_established_on=timezone.localdate() - timedelta(days=30),
    )


@pytest.fixture
def officer(unit_tree: dict[str, Unit]) -> OfficerProfile:
    return OfficerProfile.objects.create(
        actor_id="officer-001",
        role=Role.WELFARE_OFFICER,
        unit=unit_tree["battalion"],
        force_code="CAPF",
        training_valid_until=timezone.localdate() + timedelta(days=180),
    )


@pytest.fixture
def officer_principal() -> Principal:
    return Principal(
        actor_id="officer-001",
        role=Role.WELFARE_OFFICER,
        force_code="CAPF",
        unit_code="12BN",
        auth_methods=frozenset({"pwd", "otp"}),
    )


@pytest.fixture
def consent_text(db: None) -> ConsentTextVersion:
    del db
    return ConsentTextVersion.objects.create(
        version="1.0.0",
        language_code="en",
        device_tier=DeviceTier.A,
        body="Plain-language description of what is collected and why.",
        checksum="0" * 64,
        effective_from=timezone.now() - timedelta(days=1),
    )


@pytest.fixture
def audit_kwargs() -> dict[str, str]:
    """The minimum a valid audit row needs, for tests not about audit content."""
    return {
        "actor_id": "officer-001",
        "actor_role": Role.WELFARE_OFFICER,
        "action": "data.individual_read",
        "purpose_code": PurposeCode.CASE_REVIEW,
        "legal_basis": LegalBasis.CONSENT,
    }
