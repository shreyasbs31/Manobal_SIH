"""Seed a synthetic formation so the local consoles have something to show."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from manobal_core.apps.governance.enums import DataType, DeviceTier, Role
from manobal_core.apps.governance.models import (
    Case,
    ConsentEntry,
    ConsentTextVersion,
    OfficerProfile,
    Subject,
    Unit,
    UnitAggregate,
)
from manobal_core.scoring.orchestrator import persist_assessment
from manobal_risk.types import DOMAIN_CATEGORY, Domain, RiskAssessment
from manobal_risk.types import Tier as EngineTier


class Command(BaseCommand):
    help = "Create the local demonstration units, officers, subjects and cases."

    def handle(self, *args: object, **options: object) -> None:
        del args, options
        units = _units()
        text = _consent_text()
        _officers(units["battalion"])
        tokens = _subject_tokens()
        subjects = [_subject(units["company"], token, index) for index, token in enumerate(tokens)]
        Subject.objects.filter(subject_token__in=[row.subject_token for row in subjects]).update(
            created_at=timezone.now() - timedelta(days=30)
        )
        UnitAggregate.objects.filter(unit=units["company"]).delete()
        for subject in subjects:
            subject.refresh_from_db()
            _grant_all(subject, text)
        if not Case.objects.exists():
            persist_assessment(_engine(subjects[0].subject_token, EngineTier.T2), subjects[0])
            persist_assessment(_engine(subjects[1].subject_token, EngineTier.T3), subjects[1])
            persist_assessment(
                _engine(subjects[2].subject_token, EngineTier.T4, acute=True), subjects[2]
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"seeded {len(subjects)} subjects; personnel token {subjects[0].subject_token}"
            )
        )


def _units() -> dict[str, Unit]:
    force, _ = Unit.objects.get_or_create(
        code="CENTRAL",
        defaults={"name": "Central Force", "force_code": "CAPF", "depth": 0, "path": "CENTRAL"},
    )
    battalion, _ = Unit.objects.get_or_create(
        code="12BN",
        defaults={
            "name": "12 Battalion",
            "force_code": "CAPF",
            "parent": force,
            "depth": 1,
            "path": "CENTRAL/12BN",
        },
    )
    company, _ = Unit.objects.get_or_create(
        code="12BN_A",
        defaults={
            "name": "A Company",
            "force_code": "CAPF",
            "parent": battalion,
            "depth": 2,
            "path": "CENTRAL/12BN/12BN_A",
            "posted_strength": 120,
        },
    )
    return {"force": force, "battalion": battalion, "company": company}


def _consent_text() -> ConsentTextVersion:
    text, _ = ConsentTextVersion.objects.get_or_create(
        version="1.0.0",
        language_code="en",
        device_tier=DeviceTier.A,
        defaults={
            "body": "MANOBAL collects duty, optional check-ins and optional device signals "
            "to support unit welfare. You may withdraw any type at any time.",
            "checksum": "a" * 64,
            "effective_from": timezone.now() - timedelta(days=1),
        },
    )
    return text


def _officers(battalion: Unit) -> None:
    for actor_id, role in (
        ("officer-001", Role.WELFARE_OFFICER),
        ("medical-001", Role.MEDICAL_OFFICER),
        ("commander-001", Role.COMMANDER),
        ("wdec-001", Role.WDEC_AUDITOR),
    ):
        OfficerProfile.objects.get_or_create(
            actor_id=actor_id,
            defaults={
                "role": role,
                "unit": battalion,
                "force_code": "CAPF",
                "training_valid_until": timezone.localdate() + timedelta(days=180),
            },
        )


def _subject_tokens() -> list[str]:
    mapped = Path(settings.REPO_ROOT) / ".local" / "token-map.json"
    if mapped.is_file():
        payload = json.loads(mapped.read_text(encoding="utf-8"))
        tokens = [str(token) for token in payload.get("tokens", {}).values()]
        if tokens:
            return tokens
    return [f"tok_seed_{index:04d}" for index in range(12)]


def _subject(unit: Unit, token: str, index: int) -> Subject:
    subject, _ = Subject.objects.get_or_create(
        subject_token=token,
        defaults={
            "unit": unit,
            "force_code": "CAPF",
            "rank_band": "constable",
            "service_years_bucket": "5-9",
            "enrolled_at": timezone.now() - timedelta(days=60),
            "baseline_established_on": timezone.localdate() - timedelta(days=30),
        },
    )
    del index
    return subject


def _grant_all(subject: Subject, text: ConsentTextVersion) -> None:
    for data_type in (
        DataType.ORG,
        DataType.SELF_REPORT,
        DataType.BIOMETRIC,
        DataType.VOICE_FEATURES,
        DataType.JOURNAL,
    ):
        if ConsentEntry.current_for(subject.subject_token).get(data_type):
            continue
        ConsentEntry.objects.create(
            subject_token=subject.subject_token,
            data_type=data_type,
            granted=True,
            consent_text=text,
            method="app",
        )


def _engine(token: str, tier: EngineTier, *, acute: bool = False) -> RiskAssessment:
    categories = ("workload_and_duty", "leave_and_time_off")
    return RiskAssessment(
        subject_token=token,
        assessed_at=timezone.now(),
        tier=tier,
        contributing_categories=categories,
        contributing_domains=tuple(
            domain for domain, name in DOMAIN_CATEGORY.items() if name in categories
        ),
        domain_coverage=tuple((domain, True) for domain in Domain),
        ruleset_version="1.0.0-local",
        ruleset_sha256="b" * 64,
        corroborated=True,
        acute_override=acute,
        insufficient_coverage=False,
    )
