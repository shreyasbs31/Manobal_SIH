from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Annotated

import typer

from .persist import seed_primary, write_artifacts
from .personas import PERSONAS, PLAYBOOKS
from .world import generate_world

app = typer.Typer(
    name="synth",
    help="Generate and manage the fictional MANOBAL demo world.",
    no_args_is_help=True,
)


def _snapshot_path(name: str) -> Path:
    cleaned = name.replace("-", "").replace("_", "")
    if not cleaned.isalnum():
        raise typer.BadParameter("snapshot name contains unsupported characters")
    directory = Path(__file__).resolve().parents[1] / "snapshots"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{name}.dump"


@app.command("personas")
def list_personas() -> None:
    payload = []
    for persona in PERSONAS:
        play = PLAYBOOKS[persona.id]
        payload.append(
            {
                **persona.model_dump(),
                "story": play.story,
                "expected_tier": play.expected_tier,
                "expected_levers": list(play.expected_levers),
                "consents": list(play.consents),
                "helpers": list(play.helpers),
                "lifecycle_state": play.lifecycle_state,
            }
        )
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@app.command("generate")
def generate(
    world: Annotated[str, typer.Option("--world")] = "primary",
    personnel: Annotated[int, typer.Option("--personnel", min=8)] = 7200,
    days: Annotated[int, typer.Option("--days", min=30)] = 540,
    seed_value: Annotated[int, typer.Option("--seed")] = 20260916,
) -> None:
    generated = generate_world(
        world=world,
        personnel=personnel,
        days=days,
        seed=seed_value,
    )
    path = write_artifacts(generated)
    plan = generated.persist_plan()
    typer.echo(
        json.dumps(
            {
                "world": generated.name,
                "personnel": generated.personnel,
                "days": generated.days,
                "seed": generated.seed,
                "companies": generated.meta["companies"],
                "causal_order": generated.meta["causal_order"],
                "sample_tokens": len(generated.sample_tokens),
                "duty_rows": generated.duty.height,
                "ema_rows": generated.ema.height,
                "indicator_people": plan["indicator_people"],
                "artifacts": str(path),
                "synthetic": True,
            },
            sort_keys=True,
        )
    )


@app.command("seed")
def seed(
    personnel: Annotated[int, typer.Option("--personnel", min=8)] = 7200,
    days: Annotated[int, typer.Option("--days", min=30)] = 540,
    seed_value: Annotated[int, typer.Option("--seed")] = 20260916,
) -> None:
    result = seed_primary(personnel=personnel, days=days, seed=seed_value)
    typer.echo(json.dumps(result, sort_keys=True, default=str))


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
    typer.echo(json.dumps({"status": "saved", "snapshot": name, "path": str(path)}))


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
