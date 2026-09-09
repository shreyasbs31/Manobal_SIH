"""Requirement: the same ``--seed`` produces byte-identical output.

Byte-identical is the bar, not statistically-identical. A backtest that cannot
be re-run exactly is not evidence, and SDD §10.5 recalibration compares runs
against each other.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from manobal_synth import GenerationConfig, build_dataset, write_dataset
from manobal_synth.config import MissingnessProfile, OutputFormat
from manobal_synth.rng import substream

SMALL = {
    "personnel": 24,
    "duration_days": 150,
    "distress_cohort": 0.25,
    "gaming_cohort": 0.1,
    "acute_events": 0.1,
}


def _digest(directory: Path) -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.iterdir())
    }


def _generate(tmp_path: Path, name: str, **overrides: object) -> Path:
    directory = tmp_path / name
    config = GenerationConfig(**{**SMALL, **overrides})  # type: ignore[arg-type]
    write_dataset(build_dataset(config), directory)
    return directory


def test_same_seed_is_byte_identical(tmp_path: Path) -> None:
    first = _generate(tmp_path, "a", seed=4242)
    second = _generate(tmp_path, "b", seed=4242)
    assert _digest(first) == _digest(second)


def test_different_seed_differs(tmp_path: Path) -> None:
    first = _generate(tmp_path, "a", seed=4242)
    second = _generate(tmp_path, "c", seed=4243)
    changed = {
        name
        for name, digest in _digest(first).items()
        if _digest(second).get(name) != digest and name != "manifest.json"
    }
    assert "observations.jsonl" in changed
    assert "subjects.jsonl" in changed


def test_manifest_records_the_seed_and_every_parameter(tmp_path: Path) -> None:
    directory = _generate(tmp_path, "m", seed=99)
    manifest = (directory / "manifest.json").read_text()
    assert '"seed": 99' in manifest
    for parameter in ("personnel", "duration_days", "distress_onset", "fairness_profile"):
        assert f'"{parameter}"' in manifest


def test_csv_output_is_also_deterministic(tmp_path: Path) -> None:
    first = _generate(tmp_path, "csv_a", seed=7, output_format=OutputFormat.CSV)
    second = _generate(tmp_path, "csv_b", seed=7, output_format=OutputFormat.CSV)
    assert _digest(first) == _digest(second)
    assert (first / "observations.csv").is_file()


def test_row_counts_do_not_depend_on_unrelated_parameters(tmp_path: Path) -> None:
    """Substreams are label-addressed, so an unrelated knob must not reshuffle.

    This is the property that lets a reviewer change ``--missingness`` and read
    the difference as an effect of missingness rather than of a different draw
    sequence.
    """
    base = build_dataset(GenerationConfig(seed=11, **SMALL))  # type: ignore[arg-type]
    other = build_dataset(
        GenerationConfig(seed=11, missingness=MissingnessProfile.NONE, **SMALL)  # type: ignore[arg-type]
    )
    assert [s.code for s in base.units] == [s.code for s in other.units]
    assert [s.subject.subject_token for s in base.iter_subjects()] == [
        s.subject.subject_token for s in other.iter_subjects()
    ]


@pytest.mark.parametrize("label", ["units", "cohorts", "consent"])
def test_substreams_are_stable_for_a_label(label: str) -> None:
    left = substream(2026, label).normal(size=8)
    right = substream(2026, label).normal(size=8)
    assert (left == right).all()


def test_substreams_differ_between_labels() -> None:
    assert not (
        substream(2026, "units").normal(size=8) == substream(2026, "x").normal(size=8)
    ).all()
