"""``manobal-synth`` — the SDD Appendix A.3 command line.

Writes to stdout through one helper for the same reason ``manobal_risk.cli`` does:
``print`` is banned in this codebase by lint rule, and a single choke point means
a future switch to structured logging is one function to change.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from .config import (
    DEFAULT_SEED,
    DEFAULT_START_DATE,
    ConsentProfile,
    DeploymentModel,
    DistressOnset,
    FairnessProfile,
    GenerationConfig,
    MissingnessProfile,
    OutputFormat,
    RankDistribution,
)
from .dataset import build_dataset
from .errors import ManobalSynthError
from .version import GENERATOR_VERSION
from .writer import write_dataset


def _write(message: str) -> None:
    sys.stdout.write(message + "\n")


def _add_generate_arguments(parser: argparse.ArgumentParser, *, require_output: bool) -> None:
    parser.add_argument("--personnel", type=int, default=80_000)
    parser.add_argument("--duration-days", type=int, default=540)
    # Sectors and units default to a personnel-scaled layout so that the smoke
    # command is two flags long rather than five.
    parser.add_argument("--sectors", type=int, default=None)
    parser.add_argument("--units", type=int, default=None)
    parser.add_argument(
        "--rank-distribution",
        choices=[str(value) for value in RankDistribution],
        default=str(RankDistribution.CRPF_ACTUAL),
    )
    parser.add_argument("--enrolment-rate", type=float, default=0.42)
    parser.add_argument(
        "--consent-profile",
        choices=[str(value) for value in ConsentProfile],
        default=str(ConsentProfile.REALISTIC),
    )
    parser.add_argument(
        "--missingness",
        choices=[str(value) for value in MissingnessProfile],
        default=str(MissingnessProfile.REALISTIC),
    )
    parser.add_argument(
        "--deployment-model",
        choices=[str(value) for value in DeploymentModel],
        default=str(DeploymentModel.INSURGENCY_MIXED),
    )
    parser.add_argument("--incidents-per-year", type=float, default=12.0)
    parser.add_argument("--distress-cohort", type=float, default=0.06)
    parser.add_argument(
        "--distress-onset",
        choices=[str(value) for value in DistressOnset],
        default=str(DistressOnset.WEIBULL),
    )
    parser.add_argument("--acute-events", type=float, default=0.004)
    parser.add_argument("--gaming-cohort", type=float, default=0.02)
    parser.add_argument(
        "--fairness-profile",
        choices=[str(value) for value in FairnessProfile],
        default=str(FairnessProfile.NEUTRAL),
        help="skewed injects a rank-band disparity so the SDD 9.6 parity test can fail",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path, required=require_output, default=None)
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=[str(value) for value in OutputFormat],
        default=str(OutputFormat.JSONL),
    )
    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        default=DEFAULT_START_DATE,
        help="fixed default; the generator never reads the clock",
    )


def config_from_args(args: argparse.Namespace) -> GenerationConfig:
    """Build a validated config from parsed arguments."""
    return GenerationConfig(
        seed=args.seed,
        personnel=args.personnel,
        duration_days=args.duration_days,
        sectors=args.sectors,
        units=args.units,
        rank_distribution=RankDistribution(args.rank_distribution),
        enrolment_rate=args.enrolment_rate,
        consent_profile=ConsentProfile(args.consent_profile),
        missingness=MissingnessProfile(args.missingness),
        deployment_model=DeploymentModel(args.deployment_model),
        incidents_per_year=args.incidents_per_year,
        distress_cohort=args.distress_cohort,
        distress_onset=DistressOnset(args.distress_onset),
        acute_events=args.acute_events,
        gaming_cohort=args.gaming_cohort,
        fairness_profile=FairnessProfile(args.fairness_profile),
        output_format=OutputFormat(args.output_format),
        start_date=args.start_date,
    )


def _cmd_generate(args: argparse.Namespace) -> int:
    config = config_from_args(args)
    manifest = write_dataset(build_dataset(config), Path(args.output))
    _write(
        json.dumps(
            {
                "output": str(Path(args.output).resolve()),
                "generator_version": manifest.generator_version,
                "seed": config.seed,
                "row_counts": {
                    name: summary.rows for name, summary in sorted(manifest.files.items())
                },
                "total_rows": manifest.total_rows,
            },
            indent=2,
        )
    )
    return 0


def _cmd_describe(args: argparse.Namespace) -> int:
    """Print the resolved parameters without generating anything.

    Exists so that a reviewer can check what a long command line will actually
    do — including the defaulted sector and unit counts — before committing to a
    run that writes hundreds of millions of rows.
    """
    config = config_from_args(args)
    _write(json.dumps(config.as_manifest_parameters(), indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="manobal-synth", description=__doc__)
    parser.add_argument("--version", action="version", version=GENERATOR_VERSION)
    sub = parser.add_subparsers(dest="command", required=True)

    generate = sub.add_parser("generate", help="generate a synthetic corpus")
    _add_generate_arguments(generate, require_output=True)
    generate.set_defaults(func=_cmd_generate)

    describe = sub.add_parser("describe", help="print resolved parameters and exit")
    _add_generate_arguments(describe, require_output=False)
    describe.set_defaults(func=_cmd_describe)

    args = parser.parse_args(argv)
    try:
        result: int = args.func(args)
    except ManobalSynthError as exc:
        _write(f"error: {exc}")
        return 1
    return result


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
