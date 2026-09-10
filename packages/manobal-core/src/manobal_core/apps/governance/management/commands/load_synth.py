"""Load a small synthetic cohort into the five analytics stores."""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from manobal_core.apps.governance.enums import DeviceTier
from manobal_core.apps.governance.models import ConsentTextVersion, Unit
from manobal_core.synth.load import load_observation_rows
from manobal_synth import ConsentProfile, GenerationConfig, MissingnessProfile, build_dataset


class Command(BaseCommand):
    help = "Generate a tiny synthetic cohort and write it into the analytics stores."

    def add_arguments(self, parser) -> None:  # type: ignore[no-untyped-def]
        parser.add_argument("--personnel", type=int, default=12)
        parser.add_argument("--days", type=int, default=60)
        parser.add_argument("--seed", type=int, default=20260910)

    def handle(self, *args: object, **options: object) -> None:
        del args
        unit, _ = Unit.objects.get_or_create(
            code="12BN_A",
            defaults={
                "name": "A Company",
                "force_code": "CAPF",
                "depth": 2,
                "path": "CENTRAL/12BN/12BN_A",
            },
        )
        text, _ = ConsentTextVersion.objects.get_or_create(
            version="1.0.0",
            language_code="en",
            device_tier=DeviceTier.A,
            defaults={
                "body": "Synthetic load consent text.",
                "checksum": "s" * 64,
                "effective_from": timezone.now(),
            },
        )
        config = GenerationConfig(
            seed=int(options["seed"]),
            personnel=int(options["personnel"]),
            duration_days=int(options["days"]),
            units=1,
            sectors=1,
            enrolment_rate=1.0,
            consent_profile=ConsentProfile.FULL,
            missingness=MissingnessProfile.NONE,
        )
        rows = []
        for bundle in build_dataset(config).iter_subjects():
            rows.extend(bundle.observations)
        receipt = load_observation_rows(rows, unit=unit, consent_text=text)
        self.stdout.write(
            self.style.SUCCESS(
                f"loaded {receipt.subjects} subjects / {receipt.observations} observations"
            )
        )
