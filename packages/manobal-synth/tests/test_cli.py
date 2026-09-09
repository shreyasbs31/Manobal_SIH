"""The Appendix A.3 command line, exercised end to end against ``tmp_path``."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from manobal_synth.cli import main
from manobal_synth.config import DEFAULT_SEED
from manobal_synth.indicators import INDICATORS

EXPECTED_FILES = (
    "subjects.jsonl",
    "units.jsonl",
    "observations.jsonl",
    "consent.jsonl",
    "acute_triggers.jsonl",
    "incidents.jsonl",
    "ground_truth.jsonl",
    "manifest.json",
)

SMOKE = ["generate", "--personnel", "50", "--duration-days", "120", "--seed", "20260908"]


def test_smoke_run_writes_every_file(tmp_path: Path) -> None:
    assert main([*SMOKE, "--output", str(tmp_path)]) == 0
    assert {path.name for path in tmp_path.iterdir()} == set(EXPECTED_FILES)


def test_seed_defaults_so_the_smoke_command_is_two_flags_long(tmp_path: Path) -> None:
    """A default seed, not an entropy draw — an unseeded run would be useless."""
    argv = ["generate", "--personnel", "50", "--duration-days", "120", "--output", str(tmp_path)]
    assert main(argv) == 0
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["parameters"]["seed"] == DEFAULT_SEED


def test_observation_rows_have_the_engine_contract(tmp_path: Path) -> None:
    main([*SMOKE, "--output", str(tmp_path)])
    with (tmp_path / "observations.jsonl").open(encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle]
    assert rows
    for row in rows[:200]:
        assert set(row) == {"subject_token", "indicator_code", "observed_on", "value"}
        assert row["indicator_code"] in INDICATORS
        assert row["subject_token"].startswith("st_")
        assert len(row["subject_token"]) == 29


def test_manifest_records_parameters_seed_version_and_counts(tmp_path: Path) -> None:
    main([*SMOKE, "--output", str(tmp_path)])
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["parameters"]["seed"] == 20260908
    assert manifest["parameters"]["personnel"] == 50
    assert manifest["generator_version"]
    assert manifest["files"]["observations"]["rows"] > 0
    assert manifest["total_rows"] == sum(f["rows"] for f in manifest["files"].values())


def test_full_appendix_a3_invocation_parses(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Every flag from the SDD's example, at a size that runs in seconds."""
    exit_code = main(
        [
            "generate",
            "--personnel",
            "60",
            "--sectors",
            "2",
            "--units",
            "6",
            "--duration-days",
            "120",
            "--rank-distribution",
            "crpf_actual",
            "--enrolment-rate",
            "0.42",
            "--consent-profile",
            "realistic",
            "--missingness",
            "realistic",
            "--deployment-model",
            "insurgency_mixed",
            "--incidents-per-year",
            "12",
            "--distress-cohort",
            "0.06",
            "--distress-onset",
            "weibull",
            "--acute-events",
            "0.004",
            "--gaming-cohort",
            "0.02",
            "--seed",
            "20260908",
            "--output",
            str(tmp_path),
        ]
    )
    assert exit_code == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["seed"] == 20260908
    assert summary["row_counts"]["units"] == 6


def test_csv_format_writes_headers(tmp_path: Path) -> None:
    main([*SMOKE, "--output", str(tmp_path), "--format", "parquet-free-csv"])
    with (tmp_path / "observations.csv").open(encoding="utf-8", newline="") as handle:
        header = next(csv.reader(handle))
    assert header == ["subject_token", "indicator_code", "observed_on", "value"]


def test_describe_reports_resolved_defaults_without_writing(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["describe", "--personnel", "800", "--seed", "1"]) == 0
    parameters = json.loads(capsys.readouterr().out)
    assert parameters["personnel"] == 800
    # Sectors and units default from personnel. Seeing the resolved layout
    # before committing to a full run is the point of the subcommand, so the
    # manifest carries both the request (null here) and what it resolved to.
    assert parameters["sectors"] is None
    assert parameters["resolved_sectors"] >= 1
    assert parameters["resolved_units"] >= 1


def test_invalid_parameters_exit_non_zero_with_a_message(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main([*SMOKE, "--output", str(tmp_path), "--distress-cohort", "1.4"])
    assert exit_code == 1
    assert "error:" in capsys.readouterr().out


def test_fairness_profiles_are_selectable(tmp_path: Path) -> None:
    for profile in ("neutral", "skewed"):
        target = tmp_path / profile
        assert main([*SMOKE, "--output", str(target), "--fairness-profile", profile]) == 0


def test_version_flag_exits_cleanly() -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
