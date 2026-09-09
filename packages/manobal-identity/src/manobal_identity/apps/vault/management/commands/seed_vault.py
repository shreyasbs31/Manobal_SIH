"""Enrol synthetic people in the identity vault and write the token map."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from django.core.management.base import BaseCommand

from manobal_identity.api.runtime import get_vault
from manobal_identity.apps.vault.services import CallerContext, PersonRecord

_PEOPLE = (
    ("CRPF-SEED-0001", "Asha Verma", "CT"),
    ("CRPF-SEED-0002", "Ravi Kumar", "CT"),
    ("CRPF-SEED-0003", "Imran Khan", "LNK"),
    ("CRPF-SEED-0004", "Priya Nair", "CT"),
    ("CRPF-SEED-0005", "Suresh Yadav", "CT"),
    ("CRPF-SEED-0006", "Meera Joshi", "HC"),
    ("CRPF-SEED-0007", "Arjun Singh", "CT"),
    ("CRPF-SEED-0008", "Farida Begum", "CT"),
    ("CRPF-SEED-0009", "Nikhil Rao", "LNK"),
    ("CRPF-SEED-0010", "Kavita Das", "CT"),
    ("CRPF-SEED-0011", "Mohit Pal", "CT"),
    ("CRPF-SEED-0012", "Sana Sheikh", "CT"),
)


class Command(BaseCommand):
    help = "Tokenise the local demonstration cohort into iam_vault."

    def handle(self, *args: object, **options: object) -> None:
        del args, options
        people = [
            PersonRecord(
                service_no=service_no,
                full_name=name,
                rank_code=rank,
                mobile_e164=f"+91980000{index:04d}",
                unit_code="12BN_A",
                unit_path="CENTRAL/12BN/12BN_A",
                force_code="CAPF",
                enrolled_on=datetime(2024, 1, 1, tzinfo=UTC),
            )
            for index, (service_no, name, rank) in enumerate(_PEOPLE, start=1)
        ]
        tokens = get_vault().tokenise(
            people,
            CallerContext(workload_id="spiffe://manobal/ns/manobal-core/sa/ingest-worker"),
        )
        out = _repo_root() / ".local" / "token-map.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps({"tokens": tokens}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self.stdout.write(self.style.SUCCESS(f"enrolled {len(tokens)} identities → {out}"))


def _repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pyproject.toml").is_file() and (candidate / "packages").is_dir():
            return candidate
    raise RuntimeError("cannot locate the MANOBAL repository root")
