from __future__ import annotations

import json
import os
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import httpx
import polars as pl
import psycopg
from psycopg.types.json import Jsonb

from .org import build_units
from .personas import PERSONAS
from .world import SIM_NOW, World, generate_world

ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts"
SECONDARY_INDEXES = (
    "ix_unit_path_gist",
    "ix_subject_unit_path",
    "ix_officer_unit_path",
    "ix_officer_active_assignment",
    "ix_consent_ledger_token_at",
    "ix_rights_request_status_due",
    "ix_leave_event_token_applied",
    "ix_org_event_token_at",
    "ix_deployment_event_unit_path",
    "ix_incident_unit_path",
    "ix_ema_token_at",
    "ix_instrument_token_at",
    "ix_voice_features_token_at",
    "ix_climate_pulse_unit_path",
    "ix_grievance_unit_path",
    "ix_grievance_status_sla",
    "ix_regime_token_started",
    "ix_assessment_token_date",
    "ix_assessment_final_tier_date",
)


def write_artifacts(world: World, directory: Path | None = None) -> Path:
    root = directory or (ARTIFACTS / world.name)
    root.mkdir(parents=True, exist_ok=True)
    compact = {
        "subjects": world.subjects,
        "leave_event": world.leave_event,
        "leave_balance": world.leave_balance.drop("other")
        if "other" in world.leave_balance.columns
        else world.leave_balance,
        "org_event": world.org_event.drop("meta")
        if "meta" in world.org_event.columns
        else world.org_event,
        "deployment_event": world.deployment_event,
        "incident": world.incident,
        "ema": world.ema,
        "instrument": world.instrument.drop("items")
        if "items" in world.instrument.columns
        else world.instrument,
        "bio_day": world.bio_day,
        "engagement_day": world.engagement_day,
        "climate_pulse": world.climate_pulse,
        "grievance": world.grievance.drop("token")
        if "token" in world.grievance.columns
        else world.grievance,
        "buddy_pair": world.buddy_pair,
        "consent_ledger": world.consent_ledger,
        "fairness": world.fairness,
        "ground_truth": world.ground_truth,
        "officers": world.officers,
    }
    for name, frame in compact.items():
        if frame.height:
            frame.write_parquet(root / f"{name}.parquet")
    (root / "meta.json").write_text(
        json.dumps(world.meta, default=str, sort_keys=True),
        encoding="utf-8",
    )
    return root


def tokenise_world(
    world: World,
    vault_url: str,
    ingest_secret: str,
    *,
    workers: int = 32,
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    rows = world.subjects.select(["token", "service_no", "display_label", "unit_path"]).to_dicts()

    def one(row: dict[str, object]) -> tuple[str, str]:
        with httpx.Client(base_url=vault_url, timeout=30) as client:
            response = client.post(
                "/tokenise",
                headers={"x-ingest-token": ingest_secret},
                json={
                    "service_no": row["service_no"],
                    "name": row["display_label"],
                    "phone": f"SYN-PHONE-{row['service_no'][4:]}",
                    "posting": str(row["unit_path"]),
                    "synthetic": True,
                },
            )
            response.raise_for_status()
            return str(row["token"]), str(response.json()["token"])

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(one, row) for row in rows]
        for future in as_completed(futures):
            old, new = future.result()
            mapping[old] = new
    for persona in PERSONAS:
        if mapping.get(persona.token) != persona.token:
            raise RuntimeError(f"Persona token mismatch for {persona.id}")
    return mapping


def apply_token_map(world: World, mapping: dict[str, str]) -> World:
    if not mapping:
        return world

    def remap(frame: pl.DataFrame, columns: Iterable[str]) -> pl.DataFrame:
        out = frame
        for column in columns:
            if column in out.columns:
                out = out.with_columns(pl.col(column).replace(mapping, default=None).alias(column))
        return out

    world.subjects = remap(world.subjects, ["token"])
    world.duty = remap(world.duty, ["token"])
    world.leave_event = remap(world.leave_event, ["token"])
    world.leave_balance = remap(world.leave_balance, ["token"])
    world.org_event = remap(world.org_event, ["token"])
    world.ema = remap(world.ema, ["token"])
    world.instrument = remap(world.instrument, ["token"])
    world.bio_day = remap(world.bio_day, ["token"])
    world.voice_features = remap(world.voice_features, ["token"])
    world.engagement_day = remap(world.engagement_day, ["token"])
    world.buddy_pair = remap(world.buddy_pair, ["token_a", "token_b"])
    world.consent_ledger = remap(world.consent_ledger, ["token"])
    world.fairness = remap(world.fairness, ["token"])
    world.ground_truth = remap(world.ground_truth, ["token"])
    world.sample_tokens = tuple(mapping.get(token, token) for token in world.sample_tokens)
    return world


def persist_world(world: World, database_url: str) -> None:
    units = build_units()
    unit_ids = {unit.path: _stable(f"unit:{unit.path}") for unit in units}
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET session_replication_role = replica")
            for name in SECONDARY_INDEXES:
                cursor.execute(f"DROP INDEX IF EXISTS {name}")
            for unit in units:
                cursor.execute(
                    """
                    INSERT INTO unit (
                        id, path, name, level, theatre, climate_class,
                        altitude_class, parent_id
                    )
                    VALUES (%s, %s::ltree, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (path) DO UPDATE SET
                        name = EXCLUDED.name,
                        level = EXCLUDED.level,
                        theatre = EXCLUDED.theatre,
                        climate_class = EXCLUDED.climate_class,
                        altitude_class = EXCLUDED.altitude_class,
                        parent_id = EXCLUDED.parent_id
                    """,
                    (
                        unit_ids[unit.path],
                        unit.path,
                        unit.name,
                        unit.level,
                        unit.theatre,
                        unit.climate_class,
                        unit.altitude_class,
                        unit_ids[unit.parent] if unit.parent else None,
                    ),
                )
            _copy_subjects(cursor, world)
            _copy_frame(
                cursor,
                "subject_audit_attrs",
                ["token", "gender", "home_region", "language", "sector"],
                world.fairness,
            )
            _insert_officers(cursor, world)
            _copy_duty(cursor, world)
            _copy_simple(cursor, world)
            cursor.execute(
                "UPDATE sim_clock SET sim_now = %s, speed = 1, running = false WHERE id = 1",
                (SIM_NOW,),
            )
            cursor.execute(
                """
                SELECT hash FROM append_audit(
                    %s, %s, %s, %s::jsonb, %s, %s
                )
                """,
                (
                    "synth",
                    "world.seeded",
                    f"world:{world.name}",
                    Jsonb(
                        {
                            "personnel": world.personnel,
                            "days": world.days,
                            "sample": len(world.sample_tokens),
                            "synthetic": True,
                        }
                    ),
                    datetime.now(UTC),
                    SIM_NOW,
                ),
            )
            _recreate_indexes(cursor)
            cursor.execute("SET session_replication_role = origin")
        connection.commit()


def seed_primary(
    *,
    personnel: int = 7200,
    days: int = 540,
    seed: int = 20260916,
) -> dict[str, object]:
    database_url = os.environ.get(
        "CORE_ADMIN_DATABASE_URL",
        "postgresql://core_owner:core_owner_dev_only@localhost:5432/manobal_core",
    )
    vault_url = os.environ.get("VAULT_API_URL", "http://localhost:8100")
    ingest_secret = os.environ.get("TOKENISE_INGEST_SECRET", "ingest_dev_only_change_me")
    world = generate_world(world="primary", personnel=personnel, days=days, seed=seed)
    mapping = tokenise_world(world, vault_url, ingest_secret)
    apply_token_map(world, mapping)
    write_artifacts(world)
    persist_world(world, database_url)
    shifted = generate_world(world="shifted", personnel=min(personnel, 3000), days=days, seed=7)
    write_artifacts(shifted)
    return {
        "status": "seeded",
        "personnel": world.personnel,
        "days": world.days,
        "personas": len(PERSONAS),
        "sample": len(world.sample_tokens),
        "shifted_personnel": shifted.personnel,
        "plan": world.persist_plan(),
        "synthetic": True,
    }


def _copy_subjects(cursor: psycopg.Cursor, world: World) -> None:  # type: ignore[type-arg]
    rows = world.subjects.select(
        [
            "token",
            "unit_path",
            "rank_band",
            "tenure_band",
            "enrolled",
            "device_tier",
            "lifecycle_state",
            "lifecycle_since",
        ]
    )
    csv = rows.write_csv(include_header=False)
    with cursor.copy(
        """
        COPY subject (
            token, unit_path, rank_band, tenure_band, enrolled,
            device_tier, lifecycle_state, lifecycle_since
        ) FROM STDIN WITH (FORMAT csv)
        """
    ) as copy:
        copy.write(csv)


def _copy_duty(cursor: psycopg.Cursor, world: World) -> None:  # type: ignore[type-arg]
    frame = world.duty.select(
        ["token", "date", "hours", "shift_start", "night", "rest_day", "rest_denied", "sim_at"]
    )
    csv = frame.write_csv(include_header=False)
    with cursor.copy(
        """
        COPY duty_day (
            token, date, hours, shift_start, night, rest_day, rest_denied, sim_at
        ) FROM STDIN WITH (FORMAT csv)
        """
    ) as copy:
        copy.write(csv)


def _copy_frame(
    cursor: psycopg.Cursor,  # type: ignore[type-arg]
    table: str,
    columns: list[str],
    frame: pl.DataFrame,
) -> None:
    if frame.height == 0:
        return
    available = [column for column in columns if column in frame.columns]
    csv = frame.select(available).write_csv(include_header=False)
    with cursor.copy(
        f"COPY {table} ({', '.join(available)}) FROM STDIN WITH (FORMAT csv)"
    ) as copy:
        copy.write(csv)


def _copy_simple(cursor: psycopg.Cursor, world: World) -> None:  # type: ignore[type-arg]
    _copy_frame(
        cursor,
        "leave_event",
        [
            "id",
            "token",
            "type",
            "applied_at",
            "from_date",
            "to_date",
            "status",
            "reason_code",
            "sim_at",
        ],
        world.leave_event,
    )
    _copy_frame(
        cursor,
        "leave_balance",
        ["token", "as_of", "el_days", "cl_days", "sim_at"],
        world.leave_balance,
    )
    _copy_org_events(cursor, world)
    _copy_frame(
        cursor,
        "deployment_event",
        ["id", "unit_path", "type", "at", "sim_at"],
        world.deployment_event,
    )
    _copy_frame(
        cursor,
        "incident",
        ["id", "unit_path", "type", "occurred_at", "severity", "sim_at"],
        world.incident,
    )
    _copy_ema(cursor, world)
    _copy_instruments(cursor, world)
    _copy_frame(
        cursor,
        "bio_day",
        [
            "token",
            "date",
            "sleep_min",
            "sleep_eff",
            "rhr",
            "hrv_rmssd",
            "steps",
            "spo2",
            "wear_minutes",
            "sim_at",
        ],
        world.bio_day,
    )
    _copy_voice(cursor, world)
    _copy_frame(
        cursor,
        "engagement_day",
        ["token", "date", "expected", "completed", "sim_at"],
        world.engagement_day,
    )
    _copy_frame(
        cursor,
        "climate_pulse",
        ["id", "unit_path", "week", "question_id", "response_bucket", "n", "sim_at"],
        world.climate_pulse,
    )
    grievance = world.grievance
    if "token" in grievance.columns:
        grievance = grievance.drop("token")
    if "open_days" in grievance.columns:
        grievance = grievance.drop("open_days")
    _copy_frame(
        cursor,
        "grievance",
        [
            "id",
            "token_hash",
            "unit_path",
            "category",
            "status",
            "sla_due",
            "opened_at",
            "closed_at",
            "sim_at",
        ],
        grievance,
    )
    _copy_frame(
        cursor,
        "buddy_pair",
        ["id", "token_a", "token_b", "unit_path", "since", "active", "sim_at"],
        world.buddy_pair,
    )
    _copy_frame(
        cursor,
        "consent_ledger",
        [
            "id",
            "token",
            "data_type",
            "purpose",
            "action",
            "text_hash",
            "lang",
            "app_version",
            "at",
            "sim_at",
        ],
        world.consent_ledger,
    )
    _copy_frame(
        cursor,
        "ground_truth",
        ["token", "world", "distress_onset", "acute_date", "cohort"],
        world.ground_truth,
    )


def _copy_org_events(cursor: psycopg.Cursor, world: World) -> None:  # type: ignore[type-arg]
    if world.org_event.height == 0:
        return
    for row in world.org_event.iter_rows(named=True):
        cursor.execute(
            """
            INSERT INTO org_event (id, token, type, at, meta, sim_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                row["id"],
                row["token"],
                row["type"],
                row["at"],
                Jsonb(row["meta"] if isinstance(row["meta"], dict) else {}),
                row["sim_at"],
            ),
        )


def _copy_ema(cursor: psycopg.Cursor, world: World) -> None:  # type: ignore[type-arg]
    if world.ema.height == 0:
        return
    frame = world.ema.with_columns(
        pl.col("tags").list.join("|").alias("tags_joined")
    )
    csv = frame.select(
        ["id", "token", "at", "mood", "energy", "sleep_quality", "sleep_hours", "source", "sim_at"]
    ).write_csv(include_header=False)
    with cursor.copy(
        """
        COPY ema (
            id, token, at, mood, energy, sleep_quality, sleep_hours, source, sim_at
        ) FROM STDIN WITH (FORMAT csv)
        """
    ) as copy:
        copy.write(csv)
    del csv


def _copy_instruments(cursor: psycopg.Cursor, world: World) -> None:  # type: ignore[type-arg]
    if world.instrument.height == 0:
        return
    for row in world.instrument.iter_rows(named=True):
        cursor.execute(
            """
            INSERT INTO instrument (
                id, token, at, kind, items, total, lang, validated, visibility, sim_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                row["id"],
                row["token"],
                row["at"],
                row["kind"],
                Jsonb(row["items"] if isinstance(row["items"], dict) else {"q": []}),
                row["total"],
                row["lang"],
                row["validated"],
                row["visibility"],
                row["sim_at"],
            ),
        )


def _copy_voice(cursor: psycopg.Cursor, world: World) -> None:  # type: ignore[type-arg]
    if world.voice_features.height == 0:
        return
    for row in world.voice_features.iter_rows(named=True):
        cursor.execute(
            """
            INSERT INTO voice_features (id, token, at, egemaps, duration_s, lang, sim_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                row["id"],
                row["token"],
                row["at"],
                row["egemaps"],
                row["duration_s"],
                row["lang"],
                row["sim_at"],
            ),
        )


def _insert_officers(cursor: psycopg.Cursor, world: World) -> None:  # type: ignore[type-arg]
    for row in world.officers.iter_rows(named=True):
        cursor.execute(
            """
            INSERT INTO officer (
                id, entra_oid, display_label, role, unit_path, valid_from, valid_to
            )
            VALUES (%s, %s, %s, %s, %s::ltree, %s, %s)
            ON CONFLICT (entra_oid) DO UPDATE SET
                display_label = EXCLUDED.display_label,
                role = EXCLUDED.role,
                unit_path = EXCLUDED.unit_path
            """,
            (
                row["id"],
                row["entra_oid"],
                row["display_label"],
                row["role"],
                row["unit_path"],
                row["valid_from"],
                row["valid_to"],
            ),
        )


def _recreate_indexes(cursor: psycopg.Cursor) -> None:  # type: ignore[type-arg]
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_unit_path_gist ON unit USING gist (path)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS ix_subject_unit_path ON subject USING gist (unit_path)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS ix_officer_unit_path ON officer USING gist (unit_path)"
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_consent_ledger_token_at
            ON consent_ledger (token, at DESC)
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS ix_ema_token_at ON ema (token, at DESC)"
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_leave_event_token_applied
            ON leave_event (token, applied_at DESC)
        """
    )


def _stable(value: str) -> UUID:
    from uuid import UUID, uuid5

    return uuid5(UUID("5e2809f5-f170-4f17-a4d9-2df0ca2e85ca"), value)
