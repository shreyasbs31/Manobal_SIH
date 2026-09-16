from __future__ import annotations

import hashlib
import json
import os
import subprocess
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

import httpx
import numpy as np
import polars as pl
import psycopg
import typer
from psycopg.types.json import Jsonb

from .personas import PERSONAS

app = typer.Typer(
    name="synth",
    help="Generate and manage the fictional MANOBAL demo world.",
    no_args_is_help=True,
)
NAMESPACE = uuid.UUID("5e2809f5-f170-4f17-a4d9-2df0ca2e85ca")

UNITS: tuple[tuple[str, str, str, str | None, str, str, str], ...] = (
    ("force", "Force HQ Synthetic", "force", None, "all", "temperate", "plain"),
    (
        "force.north",
        "Sector North Synthetic",
        "sector",
        "force",
        "north",
        "cold",
        "high",
    ),
    (
        "force.central",
        "Sector Central Synthetic",
        "sector",
        "force",
        "central",
        "hot-humid",
        "plain",
    ),
    (
        "force.east",
        "Sector East Synthetic",
        "sector",
        "force",
        "east",
        "hot-humid",
        "plain",
    ),
    (
        "force.capital",
        "Sector Capital Synthetic",
        "sector",
        "force",
        "capital",
        "temperate",
        "plain",
    ),
    (
        "force.central.c02",
        "Bn C-02 Synthetic",
        "battalion",
        "force.central",
        "central",
        "hot-humid",
        "plain",
    ),
    (
        "force.central.c03",
        "Bn C-03 Synthetic",
        "battalion",
        "force.central",
        "central",
        "hot-humid",
        "plain",
    ),
    (
        "force.east.e01",
        "Bn E-01 Synthetic",
        "battalion",
        "force.east",
        "east",
        "hot-humid",
        "plain",
    ),
    (
        "force.east.e02",
        "Bn E-02 Synthetic",
        "battalion",
        "force.east",
        "east",
        "hot-humid",
        "plain",
    ),
    (
        "force.north.n01",
        "Bn N-01 Synthetic",
        "battalion",
        "force.north",
        "north",
        "cold",
        "high",
    ),
    (
        "force.north.n03",
        "Bn N-03 Synthetic",
        "battalion",
        "force.north",
        "north",
        "cold",
        "high",
    ),
    (
        "force.capital.c01",
        "Bn C-01 Synthetic",
        "battalion",
        "force.capital",
        "capital",
        "temperate",
        "plain",
    ),
    (
        "force.central.c02.charlie",
        "Charlie company Synthetic",
        "company",
        "force.central.c02",
        "central",
        "hot-humid",
        "plain",
    ),
    (
        "force.central.c02.bravo",
        "Bravo company Synthetic",
        "company",
        "force.central.c02",
        "central",
        "hot-humid",
        "plain",
    ),
    (
        "force.central.c03.delta",
        "Delta company Synthetic",
        "company",
        "force.central.c03",
        "central",
        "hot-humid",
        "plain",
    ),
    (
        "force.east.e01.alpha",
        "Alpha company Synthetic",
        "company",
        "force.east.e01",
        "east",
        "hot-humid",
        "plain",
    ),
    (
        "force.east.e02.charlie",
        "Charlie company Synthetic",
        "company",
        "force.east.e02",
        "east",
        "hot-humid",
        "plain",
    ),
    (
        "force.north.n01.foxtrot",
        "Foxtrot company Synthetic",
        "company",
        "force.north.n01",
        "north",
        "cold",
        "high",
    ),
    (
        "force.north.n03.delta",
        "Delta company Synthetic",
        "company",
        "force.north.n03",
        "north",
        "cold",
        "high",
    ),
    (
        "force.capital.c01.echo",
        "Echo company Synthetic",
        "company",
        "force.capital.c01",
        "capital",
        "temperate",
        "plain",
    ),
)

OFFICERS: tuple[tuple[str, str, str, str], ...] = (
    ("uwo-sunita", "Insp. Sunita Rawat Synthetic", "uwo", "force.central.c02"),
    (
        "counsellor-anjali",
        "Ms. Anjali Deshmukh Synthetic",
        "counsellor",
        "force.central",
    ),
    ("mo-farah", "Dr. Farah Siddiqui Synthetic", "mo", "force.north.n01"),
    (
        "commander-menon",
        "Commandant R. K. Menon Synthetic",
        "commander",
        "force.central.c02",
    ),
    ("hq-central", "IG Sector Central Synthetic", "hq", "force"),
    ("wdec-kavita", "Dr. Kavita Rao Synthetic", "wdec", "force"),
    ("dpo-synthetic", "DPO Synthetic", "dpo", "force"),
    (
        "integrator-synthetic",
        "HRMS custodian Synthetic",
        "hrms_integrator",
        "force",
    ),
    ("admin-synthetic", "System admin Synthetic", "admin", "force"),
    ("director-synthetic", "Demo director Synthetic", "director", "force"),
)


def stable_id(value: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, value)


@app.command("personas")
def list_personas() -> None:
    typer.echo(
        json.dumps(
            [persona.model_dump() for persona in PERSONAS],
            indent=2,
            sort_keys=True,
        )
    )


def _tokenise_personas(vault_url: str, ingest_secret: str) -> None:
    with httpx.Client(base_url=vault_url, timeout=20) as client:
        for persona in PERSONAS:
            response = client.post(
                "/tokenise",
                headers={"x-ingest-token": ingest_secret},
                json={
                    "service_no": persona.service_no,
                    "name": persona.display_label,
                    "phone": persona.phone,
                    "posting": persona.posting,
                    "synthetic": True,
                },
            )
            response.raise_for_status()
            returned_token = response.json()["token"]
            if returned_token != persona.token:
                raise RuntimeError(f"Token mismatch for {persona.id}: {returned_token}")


def _seed_core(database_url: str) -> None:
    sim_now = datetime(2026, 9, 16, 4, 30, tzinfo=UTC)
    unit_ids = {path: stable_id(f"unit:{path}") for path, *_ in UNITS}
    officer_ids = {officer_id: stable_id(f"officer:{officer_id}") for officer_id, *_ in OFFICERS}

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            for path, name, level, parent, theatre, climate, altitude in UNITS:
                cursor.execute(
                    """
                    INSERT INTO unit (
                        id, path, name, level, theatre, climate_class,
                        altitude_class, parent_id
                    )
                    VALUES (
                        %s, %s::ltree, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (path) DO UPDATE SET
                        name = EXCLUDED.name,
                        level = EXCLUDED.level,
                        theatre = EXCLUDED.theatre,
                        climate_class = EXCLUDED.climate_class,
                        altitude_class = EXCLUDED.altitude_class,
                        parent_id = EXCLUDED.parent_id
                    """,
                    (
                        unit_ids[path],
                        path,
                        name,
                        level,
                        theatre,
                        climate,
                        altitude,
                        unit_ids[parent] if parent else None,
                    ),
                )

            for persona in PERSONAS:
                cursor.execute(
                    """
                    INSERT INTO subject (
                        token, unit_path, rank_band, tenure_band, enrolled,
                        device_tier, lifecycle_state, lifecycle_since
                    )
                    VALUES (%s, %s::ltree, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (token) DO UPDATE SET
                        unit_path = EXCLUDED.unit_path,
                        rank_band = EXCLUDED.rank_band,
                        tenure_band = EXCLUDED.tenure_band,
                        enrolled = EXCLUDED.enrolled,
                        device_tier = EXCLUDED.device_tier,
                        lifecycle_state = EXCLUDED.lifecycle_state,
                        lifecycle_since = EXCLUDED.lifecycle_since
                    """,
                    (
                        persona.token,
                        persona.unit_path,
                        persona.rank_band,
                        persona.tenure_band,
                        persona.id != "thomas",
                        "B",
                        "return_from_leave" if persona.id == "karthik" else "inducted",
                        sim_now - timedelta(days=35 if persona.id == "karthik" else 180),
                    ),
                )
                cursor.execute(
                    """
                    INSERT INTO subject_audit_attrs (
                        token, gender, home_region, language, sector
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (token) DO UPDATE SET
                        gender = EXCLUDED.gender,
                        home_region = EXCLUDED.home_region,
                        language = EXCLUDED.language,
                        sector = EXCLUDED.sector
                    """,
                    (
                        persona.token,
                        persona.gender,
                        persona.home_region,
                        persona.language,
                        persona.sector,
                    ),
                )

            for officer_id, label, role, unit_path in OFFICERS:
                cursor.execute(
                    """
                    INSERT INTO officer (
                        id, entra_oid, display_label, role, unit_path,
                        valid_from, valid_to
                    )
                    VALUES (%s, %s, %s, %s, %s::ltree, %s, NULL)
                    ON CONFLICT (entra_oid) DO UPDATE SET
                        display_label = EXCLUDED.display_label,
                        role = EXCLUDED.role,
                        unit_path = EXCLUDED.unit_path,
                        valid_from = EXCLUDED.valid_from,
                        valid_to = NULL
                    """,
                    (
                        officer_ids[officer_id],
                        f"demo-{officer_id}",
                        label,
                        role,
                        unit_path,
                        sim_now - timedelta(days=30),
                    ),
                )

            seeded_cases = {
                "arjun": ("T3", ["workload", "body_vitals"], ["REST_48H"]),
                "meena": ("T2", ["leave", "self_report"], ["LEAVE_PRIORITISE"]),
                "deepak": ("T4", ["acute"], ["MO_REFERRAL"]),
                "rajesh": (
                    "T2",
                    ["hardship", "self_report"],
                    ["GRIEVANCE_EXPEDITE", "LEGAL_AID_REFERRAL"],
                ),
            }
            for persona in PERSONAS:
                case_data = seeded_cases.get(persona.id)
                if case_data is None:
                    continue
                tier, domains, recommendations = case_data
                cursor.execute(
                    """
                    INSERT INTO "case" (
                        id, token, unit_path, tier, status, opened_at,
                        sla_due_at, assigned_uwo, dominant_domains,
                        recommended, source, sim_at
                    )
                    VALUES (
                        %s, %s, %s::ltree, %s, 'open', %s, %s, %s,
                        %s, %s, %s, %s
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        tier = EXCLUDED.tier,
                        status = EXCLUDED.status,
                        sla_due_at = EXCLUDED.sla_due_at,
                        dominant_domains = EXCLUDED.dominant_domains,
                        recommended = EXCLUDED.recommended
                    """,
                    (
                        persona.case_id,
                        persona.token,
                        persona.unit_path,
                        tier,
                        sim_now - timedelta(days=5),
                        sim_now + timedelta(minutes=15 if tier == "T4" else 1440),
                        (
                            officer_ids["uwo-sunita"]
                            if persona.unit_path.startswith("force.central.c02")
                            else None
                        ),
                        domains,
                        Jsonb(recommendations),
                        "acute" if tier == "T4" else "engine",
                        sim_now,
                    ),
                )

            cursor.execute(
                "UPDATE sim_clock SET sim_now = %s, speed = 1, running = false WHERE id = 1",
                (sim_now,),
            )
            cursor.execute(
                "SELECT EXISTS (SELECT 1 FROM audit_log WHERE action = 'foundation.seeded')"
            )
            audit_row = cursor.fetchone()
            if audit_row is None:
                raise RuntimeError("Audit seed check returned no row")
            already_audited = bool(audit_row[0])
            if not already_audited:
                cursor.execute(
                    """
                    SELECT hash FROM append_audit(
                        %s, %s, %s, %s::jsonb, %s, %s
                    )
                    """,
                    (
                        "synth",
                        "foundation.seeded",
                        "world:primary",
                        json.dumps({"personas": len(PERSONAS), "synthetic": True}),
                        datetime.now(UTC),
                        sim_now,
                    ),
                )
        connection.commit()


@app.command("seed")
def seed() -> None:
    database_url = os.environ.get(
        "CORE_ADMIN_DATABASE_URL",
        "postgresql://core_owner:core_owner_dev_only@localhost:5432/manobal_core",
    )
    vault_url = os.environ.get("VAULT_API_URL", "http://localhost:8100")
    ingest_secret = os.environ.get(
        "TOKENISE_INGEST_SECRET",
        "ingest_dev_only_change_me",
    )
    _tokenise_personas(vault_url, ingest_secret)
    _seed_core(database_url)
    typer.echo(json.dumps({"status": "seeded", "personas": len(PERSONAS), "synthetic": True}))


@app.command("generate")
def generate(
    world: Annotated[str, typer.Option("--world")] = "primary",
    personnel: Annotated[int, typer.Option("--personnel", min=1)] = 7200,
    days: Annotated[int, typer.Option("--days", min=1)] = 540,
    seed_value: Annotated[int, typer.Option("--seed")] = 20260916,
) -> None:
    if world not in {"primary", "shifted"}:
        raise typer.BadParameter("world must be primary or shifted")
    persisted_rows = min(personnel, 508) * min(days, 120)
    rng = np.random.default_rng(seed_value)
    sample = pl.DataFrame(
        {
            "subject_index": np.arange(min(persisted_rows, 10_000)),
            "signal": rng.normal(
                0.15 if world == "shifted" else 0.0,
                1.2 if world == "shifted" else 1.0,
                min(persisted_rows, 10_000),
            ),
        }
    )
    checksum = hashlib.sha256(sample.write_json().encode("utf-8")).hexdigest()
    typer.echo(
        json.dumps(
            {
                "world": world,
                "personnel": personnel,
                "days": days,
                "seed": seed_value,
                "foundation_rows": persisted_rows,
                "sample_checksum": checksum,
                "synthetic": True,
            },
            sort_keys=True,
        )
    )


def _snapshot_path(name: str) -> Path:
    if not name.replace("-", "").replace("_", "").isalnum():
        raise typer.BadParameter("snapshot name contains unsupported characters")
    directory = Path(__file__).resolve().parents[1] / "snapshots"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{name}.dump"


@app.command("snapshot")
def snapshot(name: str) -> None:
    database_url = os.environ.get(
        "CORE_ADMIN_DATABASE_URL",
        "postgresql://core_owner:core_owner_dev_only@localhost:5432/manobal_core",
    )
    path = _snapshot_path(name)
    subprocess.run(
        ["pg_dump", "--format=custom", f"--file={path}", database_url],
        check=True,
    )
    typer.echo(json.dumps({"status": "saved", "snapshot": name}))


@app.command("restore")
def restore(name: str) -> None:
    database_url = os.environ.get(
        "CORE_ADMIN_DATABASE_URL",
        "postgresql://core_owner:core_owner_dev_only@localhost:5432/manobal_core",
    )
    path = _snapshot_path(name)
    if not path.exists():
        raise typer.BadParameter("snapshot does not exist")
    subprocess.run(
        [
            "pg_restore",
            "--clean",
            "--if-exists",
            "--no-owner",
            f"--dbname={database_url}",
            str(path),
        ],
        check=True,
    )
    typer.echo(json.dumps({"status": "restored", "snapshot": name}))


if __name__ == "__main__":
    app()
