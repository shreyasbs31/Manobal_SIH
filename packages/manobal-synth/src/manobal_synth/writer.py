"""Serialisation — JSONL or CSV, plus a manifest that pins the run.

Byte-identical output for a given seed is a hard requirement, and three details
carry it. Values are rounded to each indicator's declared precision at emission
rather than at write time, so no float ever depends on a platform's repr. JSON
keys are sorted and separators are fixed, so no dict-ordering change can move a
byte. And row order is the generation order, which is the population order, which
is derived from the seed.

The manifest then records the parameters, the generator version and a SHA-256 per
file. A dataset that cannot say what produced it is not a fixture, it is a pile
of numbers — and the SDD §8.2 prohibition on staging ever holding real records
only means something if a staging dataset can prove it is synthetic.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

from .config import GenerationConfig, OutputFormat
from .dataset import Dataset
from .version import GENERATOR_VERSION

MANIFEST_NAME = "manifest.json"

OBSERVATIONS_FILE = "observations"
SUBJECTS_FILE = "subjects"
UNITS_FILE = "units"
CONSENT_FILE = "consent"
ACUTE_FILE = "acute_triggers"
INCIDENTS_FILE = "incidents"
GROUND_TRUTH_FILE = "ground_truth"

_FILES: tuple[str, ...] = (
    SUBJECTS_FILE,
    UNITS_FILE,
    OBSERVATIONS_FILE,
    CONSENT_FILE,
    ACUTE_FILE,
    INCIDENTS_FILE,
    GROUND_TRUTH_FILE,
)

#: Column order per file for the CSV format. Fixed rather than derived from the
#: first row so that a file whose first subject happens to have no acute trigger
#: still gets a header.
_COLUMNS: Mapping[str, tuple[str, ...]] = {
    SUBJECTS_FILE: (
        "subject_token",
        "unit_code",
        "sector_code",
        "region",
        "rank_band",
        "tenure_years",
        "tenure_bucket",
        "language",
        "enrolled",
        "enrolled_on",
    ),
    UNITS_FILE: (
        "unit_code",
        "sector_code",
        "region",
        "posting_class",
        "family_station",
        "assigned_strength",
    ),
    OBSERVATIONS_FILE: ("subject_token", "indicator_code", "observed_on", "value"),
    CONSENT_FILE: (
        "subject_token",
        "domain",
        "channel",
        "granted",
        "granted_on",
        "requires_opt_in",
    ),
    ACUTE_FILE: ("subject_token", "kind", "occurred_at", "source"),
    INCIDENTS_FILE: (
        "incident_id",
        "unit_code",
        "sector_code",
        "occurred_on",
        "kind",
        "severity",
    ),
    GROUND_TRUTH_FILE: (
        "subject_token",
        "cohort",
        "distressed",
        "gaming",
        "onset_day",
        "onset_on",
        "ramp_days",
        "severity",
        "strain_at_end",
        "deteriorating_at_end",
        "acute",
        "acute_on",
        "acute_kind",
        "acute_reported",
        "enrolled",
        "consented_domains",
        "rank_band",
        "sector_code",
        "unit_code",
        "tenure_bucket",
        "language",
    ),
}


class _Sink:
    """One output file, counting rows and digesting bytes as it writes."""

    __slots__ = ("_digest", "_handle", "_rows", "_writer", "name", "path")

    def __init__(self, name: str, path: Path, output_format: OutputFormat) -> None:
        self.name = name
        self.path = path
        self._rows = 0
        self._digest = hashlib.sha256()
        self._handle: TextIO = path.open("w", encoding="utf-8", newline="")
        self._writer: csv.DictWriter[str] | None = None
        if output_format is OutputFormat.CSV:
            self._writer = csv.DictWriter(
                self._handle, fieldnames=list(_COLUMNS[name]), lineterminator="\n"
            )
            self._writer.writeheader()

    def write(self, row: Mapping[str, Any]) -> None:
        if self._writer is not None:
            self._writer.writerow(dict(row))
        else:
            self._handle.write(json.dumps(dict(row), sort_keys=True, separators=(",", ":")) + "\n")
        self._rows += 1

    def close(self) -> tuple[int, str, int]:
        self._handle.close()
        payload = self.path.read_bytes()
        self._digest.update(payload)
        return self._rows, self._digest.hexdigest(), len(payload)


@dataclass(frozen=True, slots=True)
class FileSummary:
    rows: int
    sha256: str
    bytes: int

    def as_dict(self) -> dict[str, Any]:
        return {"rows": self.rows, "sha256": self.sha256, "bytes": self.bytes}


@dataclass(frozen=True, slots=True)
class Manifest:
    """What a written corpus says about itself."""

    generator_version: str
    parameters: Mapping[str, Any]
    files: Mapping[str, FileSummary]

    def as_dict(self) -> dict[str, Any]:
        return {
            "generator": "manobal-synth",
            "generator_version": self.generator_version,
            "parameters": dict(self.parameters),
            "row_counts": {name: summary.rows for name, summary in self.files.items()},
            "total_rows": self.total_rows,
            "files": {name: summary.as_dict() for name, summary in self.files.items()},
        }

    @property
    def total_rows(self) -> int:
        return sum(summary.rows for summary in self.files.values())


class _SinkSet:
    """Every output file for one run, opened together and closed together."""

    def __init__(self, directory: Path, output_format: OutputFormat) -> None:
        suffix = "jsonl" if output_format is OutputFormat.JSONL else "csv"
        self._sinks = {
            name: _Sink(name, directory / f"{name}.{suffix}", output_format) for name in _FILES
        }
        self._summaries: dict[str, FileSummary] | None = None

    def write(self, name: str, rows: Iterable[Mapping[str, Any]]) -> None:
        sink = self._sinks[name]
        for row in rows:
            sink.write(row)

    def summaries(self) -> dict[str, FileSummary]:
        """Close every file and report its row count and digest.

        Idempotent so that the failure path can close handles without having to
        know whether the success path already did.
        """
        if self._summaries is None:
            self._summaries = {}
            for name, sink in self._sinks.items():
                rows, digest, size = sink.close()
                self._summaries[name] = FileSummary(rows=rows, sha256=digest, bytes=size)
        return dict(self._summaries)


def write_dataset(dataset: Dataset, directory: Path) -> Manifest:
    """Stream a dataset to disk and return its manifest."""
    directory.mkdir(parents=True, exist_ok=True)
    sinks = _SinkSet(directory, dataset.config.output_format)
    try:
        _stream(dataset, sinks)
    except BaseException:
        sinks.summaries()
        raise

    manifest = Manifest(
        generator_version=GENERATOR_VERSION,
        parameters=dataset.config.as_manifest_parameters(),
        files=sinks.summaries(),
    )
    _write_manifest(directory, manifest)
    return manifest


def _stream(dataset: Dataset, sinks: _SinkSet) -> None:
    sinks.write(UNITS_FILE, (row.as_dict() for row in dataset.unit_rows))
    sinks.write(INCIDENTS_FILE, (row.as_dict() for row in dataset.incident_rows))
    for records in dataset.iter_subjects():
        sinks.write(SUBJECTS_FILE, (records.subject.as_dict(),))
        sinks.write(CONSENT_FILE, (row.as_dict() for row in records.consent))
        sinks.write(OBSERVATIONS_FILE, (row.as_dict() for row in records.observations))
        sinks.write(ACUTE_FILE, (row.as_dict() for row in records.acute_triggers))
        sinks.write(GROUND_TRUTH_FILE, (records.ground_truth.as_dict(),))


def _write_manifest(directory: Path, manifest: Manifest) -> None:
    path = directory / MANIFEST_NAME
    path.write_text(
        json.dumps(manifest.as_dict(), sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


def output_file_names(config: GenerationConfig) -> tuple[str, ...]:
    suffix = "jsonl" if config.output_format is OutputFormat.JSONL else "csv"
    return (*(f"{name}.{suffix}" for name in _FILES), MANIFEST_NAME)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load a written JSONL file. Used by the test suites, not by the CLI."""
    lines: Sequence[str] = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line]
