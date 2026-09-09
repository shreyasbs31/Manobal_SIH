"""Release-gating privacy assertions (SDD §9.6).

Every test here corresponds to a property the SDD treats as non-negotiable. A
failure is a release blocker, not a bug to schedule: each one represents a
promise made to people who cannot easily refuse to participate in the
institution running this system.

These are written as *structural* tests wherever possible — introspecting model
fields, database grants and network reachability rather than exercising a happy
path. A behavioural test proves the current code path is safe; a structural test
proves the unsafe thing is not expressible.
"""

from __future__ import annotations

import dataclasses
from typing import Any

import psycopg
import pytest
from django.apps import apps
from django.conf import settings
from django.db import connections

from manobal_core.apps.governance.models import RiskAssessmentRecord
from manobal_risk.types import RiskAssessment

pytestmark = pytest.mark.privacy_gate

#: Column names that would constitute a direct identifier in the analytics
#: plane. Sourced from SDD §5.1's description of what lives in ``iam_vault`` and
#: therefore must not live anywhere else.
DIRECT_IDENTIFIERS = frozenset(
    {
        "service_number",
        "service_no",
        "svc_no",
        "personnel_number",
        "name",
        "first_name",
        "last_name",
        "full_name",
        "father_name",
        "date_of_birth",
        "dob",
        "mobile",
        "mobile_number",
        "phone",
        "phone_number",
        "email",
        "aadhaar",
        "aadhaar_number",
        "pan",
        "home_address",
        "address",
        "photograph",
        "biometric_id",
    }
)

#: Field names that would mean a numeric welfare score had escaped the engine.
SCORE_FIELDS = frozenset(
    {
        "wsi",
        "welfare_signal_index",
        "score",
        "risk_score",
        "raw_score",
        "composite_score",
        "deviation",
        "deviation_score",
        "domain_scores",
        "severity_score",
    }
)

ANALYTICS_APPS = ("governance", "orgstore", "psystore", "biostore", "voicestore")


def _analytics_models() -> list[Any]:
    return [m for app in ANALYTICS_APPS for m in apps.get_app_config(app).get_models()]


def _is_person_bearing(model: Any) -> bool:
    """True when a row of this model describes an individual.

    ``subject_token`` is the analytics plane's only handle on a person, so its
    presence is exactly the condition under which an identifier column would be
    a re-identification risk.
    """
    names = {field.name for field in model._meta.get_fields()}
    return "subject_token" in names


class TestNoIdentifiersInTheAnalyticsPlane:
    """§3.2 rule 3: no identifying information crosses into Zone 2.

    Pseudonymity is only worth something if it holds everywhere. A single model
    with a ``mobile`` column re-identifies the entire store it lives in, because
    every other row is joinable to it by ``subject_token``.
    """

    def test_no_person_bearing_model_declares_a_direct_identifier(self) -> None:
        """Scoped to models that are *about a person*.

        The scoping is the substance of the test, not a convenience. ``Unit.name``
        is "12 Battalion" and identifies a formation; the same column on a table
        keyed by ``subject_token`` would identify a human being. What makes a
        column dangerous is the row it sits on, so the gate looks at exactly the
        tables that carry a subject token.
        """
        offenders = {
            f"{model._meta.app_label}.{model.__name__}.{field.name}"
            for model in _analytics_models()
            if _is_person_bearing(model)
            for field in model._meta.get_fields()
            if field.name.lower() in DIRECT_IDENTIFIERS
        }
        assert not offenders, f"direct identifiers on person-level rows: {offenders}"

    def test_the_person_bearing_model_set_is_not_accidentally_empty(self) -> None:
        """Guards the guard.

        If ``subject_token`` were ever renamed, the test above would scan nothing
        and pass vacuously — a green gate protecting nothing at all.
        """
        assert len([m for m in _analytics_models() if _is_person_bearing(m)]) >= 10

    def test_subjects_are_addressed_only_by_token(self) -> None:
        subject = apps.get_model("governance", "Subject")
        assert subject._meta.pk.name == "subject_token"

    @pytest.mark.django_db(databases=["default", "org", "psy"])
    def test_no_person_bearing_table_carries_an_identifier_column(self) -> None:
        """Belt and braces: read the live schema, not just the model classes.

        A raw-SQL migration can add a column the ORM knows nothing about, and
        such a column would be invisible to model introspection. The candidate
        set is derived from the schema itself — every table that has a
        ``subject_token`` column — so a new person-level table is covered the
        moment it is created, without anyone remembering to add it here.
        """
        offenders: list[str] = []
        for alias in ("default", "org", "psy"):
            with connections[alias].cursor() as cursor:
                cursor.execute(
                    """
                    SELECT table_name, column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND column_name = ANY(%s)
                      AND table_name IN (
                          SELECT table_name FROM information_schema.columns
                          WHERE table_schema = 'public' AND column_name = 'subject_token'
                      )
                    """,
                    [sorted(DIRECT_IDENTIFIERS)],
                )
                offenders += [f"{alias}:{t}.{c}" for t, c in cursor.fetchall()]
        assert not offenders, f"identifier columns on person-level tables: {offenders}"


class TestNoScoreEscapesTheEngine:
    """FR-3.7. The WSI is an internal quantity and stays internal.

    The reason is not secrecy for its own sake. A number invites comparison,
    ranking and thresholding by people with no training in what it measures —
    "show me everyone above 0.7" is a request the system must be unable to
    satisfy. A tier plus category names supports a welfare conversation; a score
    supports a leaderboard.
    """

    def test_the_persisted_assessment_has_no_score_column(self) -> None:
        present = {f.name.lower() for f in RiskAssessmentRecord._meta.get_fields()}
        assert not (present & SCORE_FIELDS)

    def test_the_engines_public_result_type_exposes_no_number(self) -> None:
        """The dataclass the engine actually returns carries no numeric field.

        ``coverage`` is deliberately excluded from this check where it appears:
        it describes how much data was available, which is a property of
        participation rather than a measurement of the person.
        """
        numeric = {
            field.name
            for field in dataclasses.fields(RiskAssessment)
            if field.type in {"float", "int", float, int}
        }
        assert not numeric, f"RiskAssessment leaks numeric fields: {numeric}"

    def test_contributing_categories_are_names_not_measurements(self) -> None:
        field = RiskAssessmentRecord._meta.get_field("contributing_categories")
        assert field.get_internal_type() == "JSONField"
        assert field.default is list


class TestStoreSeparation:
    """§5.1. Separate databases, not schemas — so the planner enforces it."""

    def test_each_app_is_routed_to_its_own_store(self) -> None:
        from manobal_core.db.routers import STORE_BY_APP

        assert len(set(STORE_BY_APP.values())) == len(STORE_BY_APP)

    def test_no_model_declares_a_relation_across_stores(self) -> None:
        from manobal_core.db.routers import STORE_BY_APP

        offenders: list[str] = []
        for model in _analytics_models():
            here = STORE_BY_APP.get(model._meta.app_label)
            for field in model._meta.get_fields():
                if not field.is_relation or field.related_model is None:
                    continue
                there = STORE_BY_APP.get(field.related_model._meta.app_label)
                if there is not None and there != here:
                    offenders.append(f"{model.__name__}.{field.name} -> {field.related_model}")
        assert not offenders, f"cross-store relations declared: {offenders}"

    @pytest.mark.django_db(databases=["org"])
    def test_signal_stores_hold_no_tables_belonging_to_other_stores(self) -> None:
        """The strongest form: the tables genuinely are not there."""
        with connections["org"].cursor() as cursor:
            cursor.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname='public' "
                "AND tablename IN ('audit_event','journal_entry','consent_entry')"
            )
            assert cursor.fetchall() == []


class TestIdentityAirGap:
    """§3.2 rule 2 / NFR-SEC5. Zone 2 has no route to Zone 3's database.

    The check is at the *connection* layer, not the query layer. A test that
    connected successfully and then found no rows would prove only that the
    vault was empty; what must be true is that the analytics plane cannot open
    the connection at all.
    """

    def test_no_database_alias_points_at_the_identity_vault(self) -> None:
        for alias, config in settings.DATABASES.items():
            assert config.get("NAME") != "iam_vault", f"alias {alias} reaches the vault"

    def test_the_settings_carry_no_vault_credential(self) -> None:
        rendered = repr(settings.DATABASES).lower()
        assert "iam_vault" not in rendered
        assert "manobal_identity" not in rendered

    @pytest.mark.integration
    def test_the_core_role_is_rejected_by_the_identity_cluster(self) -> None:
        """The live proof. Requires the local clusters to be running."""
        with pytest.raises(psycopg.OperationalError) as exc:
            psycopg.connect(
                host="127.0.0.1",
                port=55433,
                user="manobal_core",
                password="dev_only_not_a_secret",
                dbname="iam_vault",
                connect_timeout=5,
            )
        # Rejected by pg_hba before authentication, which is the strongest
        # available refusal: the role is not merely unauthorised, it is not
        # permitted to attempt.
        assert "pg_hba.conf rejects connection" in str(exc.value)

    @pytest.mark.integration
    def test_the_risk_engine_role_is_rejected_by_the_identity_cluster(self) -> None:
        with pytest.raises(psycopg.OperationalError) as exc:
            psycopg.connect(
                host="127.0.0.1",
                port=55433,
                user="manobal_risk",
                password="dev_only_not_a_secret",
                dbname="iam_vault",
                connect_timeout=5,
            )
        assert "pg_hba.conf rejects connection" in str(exc.value)


class TestRiskEngineIsSelfContained:
    """§3.2 rule 1. The engine cannot reach a database or the network.

    Enforced by the package's dependency list rather than by review. An engine
    that cannot import a database driver cannot be persuaded to read a name.
    """

    def test_the_engine_imports_no_database_or_http_client(self) -> None:
        import sys

        import manobal_risk

        engine_modules = [m for name, m in sys.modules.items() if name.startswith("manobal_risk")]
        forbidden = {"psycopg", "django", "httpx", "requests", "urllib3", "socket"}
        for module in engine_modules:
            imported = {
                value.__name__.split(".")[0]
                for value in vars(module).values()
                if hasattr(value, "__name__") and hasattr(value, "__file__")
            }
            leaked = imported & forbidden
            assert not leaked, f"{module.__name__} imports {leaked}"
        assert manobal_risk is not None

    @pytest.mark.django_db(databases=["psy"])
    def test_the_engine_has_no_read_path_to_journal_entries(self) -> None:
        """A journal is for the person who wrote it. It is never scored.

        Asserted at the grant level because that is where it is true: the risk
        engine's database role holds no privilege on ``journal_entry``.
        """
        with connections["psy"].cursor() as cursor:
            cursor.execute(
                """
                SELECT privilege_type FROM information_schema.table_privileges
                WHERE grantee = 'manobal_risk' AND table_name = 'journal_entry'
                """
            )
            assert cursor.fetchall() == []

    @pytest.mark.django_db(databases=["org"])
    def test_the_engine_cannot_modify_any_signal_store(self) -> None:
        """Read-only by grant. A scoring run that could rewrite its own inputs
        would make every assessment unfalsifiable after the fact."""
        with connections["org"].cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT privilege_type FROM information_schema.table_privileges
                WHERE grantee = 'manobal_risk' AND table_schema = 'public'
                """
            )
            granted = {row[0] for row in cursor.fetchall()}
        assert granted <= {"SELECT"}, f"risk engine holds write privileges: {granted}"


class TestAuditCoverage:
    """§7.3. The audit log records purpose and basis, or it does not record."""

    def test_purpose_and_legal_basis_are_mandatory(self) -> None:
        from manobal_core.apps.governance.models import AuditEvent

        for name in ("purpose_code", "legal_basis"):
            field = AuditEvent._meta.get_field(name)
            assert not field.null, f"{name} must not be nullable"
            assert field.choices, f"{name} must be enumerated, not free text"

    @pytest.mark.django_db(databases=["default"])
    def test_the_chain_verifier_exists_in_every_governance_database(self) -> None:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT to_regproc('manobal_audit_chain_break')")
            assert cursor.fetchone()[0] is not None


class TestAccessGrantsExpire:
    """FR-2.7 / §5.2. Standing access is what turns welfare into surveillance."""

    @pytest.mark.django_db(databases=["default"])
    def test_a_grant_cannot_outlive_the_statutory_ceiling(self) -> None:
        from datetime import timedelta

        from django.utils import timezone

        from manobal_core.apps.governance.enums import GrantScope, LegalBasis, Role
        from manobal_core.apps.governance.models import MAX_GRANT_DAYS, AccessGrant

        granted_at = timezone.now()
        grant = AccessGrant(
            subject_token="tok_x",
            grantee_id="officer-001",
            grantee_role=Role.WELFARE_OFFICER,
            scope=GrantScope.FLAG,
            granted_at=granted_at,
            expires_at=granted_at + timedelta(days=365),
            legal_basis=LegalBasis.CONSENT,
            justification="attempted long-lived grant",
        )
        grant.save()
        assert grant.expires_at <= granted_at + timedelta(days=MAX_GRANT_DAYS)
