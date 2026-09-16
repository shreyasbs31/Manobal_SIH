from __future__ import annotations

import polars as pl
import pytest
import typer
from manobal_synth.cli import _snapshot_path
from manobal_synth.org import build_units, company_paths
from manobal_synth.persist import _stable
from manobal_synth.personas import PERSONAS, PLAYBOOKS
from manobal_synth.world import generate_world


def test_org_tree_has_four_sectors_and_seventy_two_companies() -> None:
    units = build_units()
    companies = company_paths()
    sectors = [unit for unit in units if unit.level == "sector"]
    battalions = [unit for unit in units if unit.level == "battalion"]
    assert len(sectors) == 4
    assert len(battalions) == 12
    assert len(companies) == 72
    assert "force.central.c02.charlie" in companies
    assert "force.capital.c01.echo" in companies


def test_stable_ids_are_deterministic() -> None:
    assert _stable("unit:force") == _stable("unit:force")
    assert _stable("unit:force") != _stable("unit:force.central")


def test_generate_primary_small_world_follows_volume_rules() -> None:
    world = generate_world(world="primary", personnel=80, days=60, seed=20260916)
    assert world.personnel == 80
    assert world.days == 60
    assert world.duty.height == 80 * 60
    assert world.subjects.height == 80
    assert set(world.subjects["persona_id"].drop_nulls().to_list()) == {
        persona.id for persona in PERSONAS
    }
    sample = set(world.sample_tokens)
    assert {persona.token for persona in PERSONAS} <= sample
    if world.ema.height:
        assert world.ema.filter(~pl.col("token").is_in(list(sample))).height == 0
    if world.bio_day.height:
        assert world.bio_day.filter(~pl.col("token").is_in(list(sample))).height == 0
    plan = world.persist_plan()
    assert plan["indicator_people"] == len(world.sample_tokens)
    assert world.meta["causal_order"][0] == "deployment"
    assert world.meta["causal_order"][-1] == "ground_truth"


def test_persona_storylines_are_in_the_raw_signals() -> None:
    world = generate_world(world="primary", personnel=80, days=60, seed=20260916)
    arjun = next(persona.token for persona in PERSONAS if persona.id == "arjun")
    meena = next(persona.token for persona in PERSONAS if persona.id == "meena")
    thomas = next(persona.token for persona in PERSONAS if persona.id == "thomas")
    rajesh = next(persona.token for persona in PERSONAS if persona.id == "rajesh")
    rest_flags = (
        world.duty.filter(pl.col("token") == arjun).sort("date")["rest_day"].to_list()
    )
    streak = 0
    longest = 0
    for rest in rest_flags:
        if rest:
            longest = max(longest, streak)
            streak = 0
        else:
            streak += 1
    longest = max(longest, streak)
    assert longest >= 19
    meena_leave = world.leave_event.filter(
        (pl.col("token") == meena) & (pl.col("status") == "rejected")
    )
    assert meena_leave.height >= 2
    thomas_row = world.subjects.filter(pl.col("token") == thomas).row(0, named=True)
    assert thomas_row["wearable"] is False
    assert thomas_row["voice_on"] is False
    assert world.grievance.filter(pl.col("token") == rajesh).height >= 1
    assert world.incident.filter(pl.col("unit_path") == "force.central.c02.bravo").height >= 1
    assert world.consent_ledger.height == 80 * 8
    karthik = world.subjects.filter(pl.col("persona_id") == "karthik").row(0, named=True)
    assert karthik["lifecycle_state"] == "return_from_leave"


def test_shifted_world_differs_from_primary() -> None:
    primary = generate_world(world="primary", personnel=80, days=60, seed=20260916)
    shifted = generate_world(world="shifted", personnel=80, days=60, seed=7)
    assert primary.duty["hours"].mean() != shifted.duty["hours"].mean()
    assert shifted.name == "shifted"
    assert set(shifted.ground_truth["world"].to_list()) == {"shifted"}


def test_playbooks_cover_spec_five_three() -> None:
    expected = {
        "arjun": "T3",
        "meena": "T2",
        "imran": "T1",
        "thomas": "T0",
        "lalit": "T1",
        "deepak": "T0",
        "rajesh": "T2",
        "karthik": "T1",
    }
    assert {persona.id for persona in PERSONAS} == set(expected)
    for persona_id, tier in expected.items():
        assert PLAYBOOKS[persona_id].expected_tier == tier


def test_snapshot_name_rejects_unsupported_characters() -> None:
    with pytest.raises(typer.BadParameter):
        _snapshot_path("demo baseline")
    path = _snapshot_path("demo-baseline")
    assert path.name == "demo-baseline.dump"
