"""Assembly — turn a config into a stream of per-subject record bundles.

Subjects are yielded one at a time rather than collected. At the SDD's 80,000
personnel over 540 days the observation table runs to hundreds of millions of
rows, and the 1.2 M load-test figure is five times that; a generator that built a
list first would be unusable at exactly the scale it was written for. The
population, consent and cohort tables *are* held in memory, because they are a
few hundred bytes a head and every subject's series needs random access to them.

Consent is applied here rather than inside the chain. The chain generates every
domain for every subject unconditionally — a person's sleep exists whether or not
they agreed to share it — and this module decides what the platform is allowed to
have seen. That ordering is what lets a test re-run the same subject with a
different consent profile and get the same underlying person.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import date

import numpy as np

from manobal_risk import AcuteTriggerKind, Domain

from .arrays import BoolArray, FloatArray
from .chain import SubjectSeries, generate_subject_series
from .cohorts import Cohort, assign_cohorts
from .config import GenerationConfig
from .consent import ConsentState, assign_consent
from .incidents import (
    DIRECT_INVOLVEMENT_PROBABILITY,
    Incident,
    draw_incidents,
    incidents_by_unit,
    unit_pressure,
)
from .indicators import INDICATORS, OBJECTIVE_DOMAINS, format_value
from .missingness import force_hrms_outages
from .person import PersonModel, build_person
from .population import Subject, Unit, build_subjects, build_units
from .records import (
    AcuteTriggerRow,
    ConsentRow,
    GroundTruthRow,
    IncidentRow,
    ObservationRow,
    SubjectRow,
    UnitRow,
    acute_timestamp,
)
from .rng import substream
from .trajectory import is_deteriorating

#: Source string recorded on generated acute triggers, so that a consumer can
#: tell a synthetic escalation from a real one without consulting the manifest.
ACUTE_SOURCE_APP = "synthetic_app_checkin"
ACUTE_SOURCE_INCIDENT = "synthetic_incident_webhook"


@dataclass(frozen=True, slots=True)
class SubjectRecords:
    """Everything one subject contributes to the corpus."""

    subject: SubjectRow
    consent: tuple[ConsentRow, ...]
    observations: tuple[ObservationRow, ...]
    acute_triggers: tuple[AcuteTriggerRow, ...]
    ground_truth: GroundTruthRow
    #: The generated series and latents. Present for the causal and calibration
    #: tests; nothing in ``writer.py`` reads it.
    series: SubjectSeries


@dataclass(frozen=True, slots=True)
class Dataset:
    """A lazily-materialised corpus."""

    config: GenerationConfig
    units: tuple[Unit, ...]
    subjects_meta: tuple[Subject, ...]
    consents: tuple[ConsentState, ...]
    cohorts: tuple[Cohort, ...]
    incidents: tuple[Incident, ...]
    hrms_outages: BoolArray
    #: Calendar dates for day 0..N-1, built once. Rebuilding this per subject
    #: costs more than generating the series it labels.
    date_axis: tuple[date, ...]

    @property
    def unit_rows(self) -> tuple[UnitRow, ...]:
        return tuple(
            UnitRow(
                unit_code=unit.code,
                sector_code=unit.sector_code,
                region=unit.region,
                posting_class=str(unit.posting_class),
                family_station=unit.family_station,
                assigned_strength=unit.assigned_strength,
            )
            for unit in self.units
        )

    @property
    def incident_rows(self) -> tuple[IncidentRow, ...]:
        return tuple(
            IncidentRow(
                incident_id=incident.incident_id,
                unit_code=incident.unit_code,
                sector_code=incident.sector_code,
                occurred_on=self.config.day_to_date(incident.day),
                kind=incident.kind,
                severity=incident.severity,
            )
            for incident in self.incidents
        )

    def iter_subjects(self) -> Iterator[SubjectRecords]:
        pressures = self._unit_pressures()
        for subject in self.subjects_meta:
            yield self._records_for(subject, pressures[subject.unit_index])

    def _unit_pressures(self) -> dict[int, FloatArray]:
        grouped = incidents_by_unit(self.incidents)
        flat = np.zeros(self.config.duration_days, dtype=np.float64)
        return {
            unit.index: unit_pressure(grouped[unit.index], self.config.duration_days)
            if unit.index in grouped
            else flat
            for unit in self.units
        }

    def _records_for(self, subject: Subject, pressure: FloatArray) -> SubjectRecords:
        person = build_person(self.config.seed, subject)
        consent = self.consents[subject.index]
        cohort = self.cohorts[subject.index]
        series = generate_subject_series(
            self.config,
            subject,
            person,
            self.units[subject.unit_index],
            cohort,
            pressure,
            self.hrms_outages,
        )
        return SubjectRecords(
            subject=_subject_row(self.config, subject, self.units[subject.unit_index], consent),
            consent=_consent_rows(self.config, subject, consent),
            observations=tuple(_observations(self.config, series, consent, self.date_axis)),
            acute_triggers=self._acute_rows(subject, cohort, person),
            ground_truth=_ground_truth_row(self.config, subject, cohort, consent, series),
            series=series,
        )

    def _acute_rows(
        self,
        subject: Subject,
        cohort: Cohort,
        person: PersonModel,
    ) -> tuple[AcuteTriggerRow, ...]:
        rows: list[AcuteTriggerRow] = []
        if cohort.acute_day is not None and cohort.acute_reported:
            kind = cohort.acute_kind or AcuteTriggerKind.EXPLICIT_SOS
            rows.append(
                AcuteTriggerRow(
                    subject_token=subject.subject_token,
                    kind=str(kind),
                    occurred_at=acute_timestamp(
                        self.config.day_to_date(cohort.acute_day), from_incident=False
                    ),
                    source=ACUTE_SOURCE_APP,
                )
            )
        rows.extend(self._incident_involvement(subject, person))
        return tuple(rows)

    def _incident_involvement(
        self,
        subject: Subject,
        person: PersonModel,
    ) -> list[AcuteTriggerRow]:
        """Direct involvement in a unit incident, per SDD §4.7.

        This is the one acute path that needs no enrolment: the force learns
        about it through the incident webhook, not through the app, so it reaches
        personnel who never opted in to anything.
        """
        grouped = incidents_by_unit(self.incidents)
        own = grouped.get(subject.unit_index, ())
        if not own:
            return []
        rng = substream(self.config.seed, "involvement", subject.index)
        draws = rng.random(len(own))
        return [
            AcuteTriggerRow(
                subject_token=subject.subject_token,
                kind=str(AcuteTriggerKind.CRITICAL_INCIDENT),
                occurred_at=acute_timestamp(
                    self.config.day_to_date(incident.day), from_incident=True
                ),
                source=ACUTE_SOURCE_INCIDENT,
            )
            for position, incident in enumerate(own)
            if draws[position] < DIRECT_INVOLVEMENT_PROBABILITY * person.trait("reactivity")
        ]


def build_dataset(config: GenerationConfig) -> Dataset:
    """Build the population, consent, cohort and incident tables for a run."""
    units = build_units(config)
    subjects = build_subjects(config, units)
    consents = assign_consent(config, subjects)
    return Dataset(
        config=config,
        units=units,
        subjects_meta=subjects,
        consents=consents,
        cohorts=assign_cohorts(config, subjects, consents),
        incidents=draw_incidents(config, units),
        hrms_outages=force_hrms_outages(config),
        date_axis=tuple(config.day_to_date(day) for day in range(config.duration_days)),
    )


def _subject_row(
    config: GenerationConfig,
    subject: Subject,
    unit: Unit,
    consent: ConsentState,
) -> SubjectRow:
    return SubjectRow(
        subject_token=subject.subject_token,
        unit_code=unit.code,
        sector_code=unit.sector_code,
        region=unit.region,
        rank_band=str(subject.rank_band),
        tenure_years=subject.tenure_years,
        tenure_bucket=str(subject.tenure_bucket),
        language=subject.language,
        enrolled=consent.enrolled,
        enrolled_on=(
            config.day_to_date(consent.enrolled_on_day).isoformat() if consent.enrolled else None
        ),
    )


def _consent_rows(
    config: GenerationConfig,
    subject: Subject,
    consent: ConsentState,
) -> tuple[ConsentRow, ...]:
    granted_on = (
        config.day_to_date(consent.enrolled_on_day).isoformat() if consent.enrolled else None
    )
    rows: list[ConsentRow] = []
    for domain in sorted(Domain, key=lambda item: item.value):
        objective = domain in OBJECTIVE_DOMAINS
        granted = objective or domain in consent.granted
        rows.append(
            ConsentRow(
                subject_token=subject.subject_token,
                domain=domain.value,
                channel=_channel_for(domain),
                granted=granted,
                granted_on=None if objective else (granted_on if granted else None),
                requires_opt_in=not objective,
            )
        )
    return tuple(rows)


def _channel_for(domain: Domain) -> str:
    codes = [code for code, spec in INDICATORS.items() if spec.domain is domain]
    return str(INDICATORS[codes[0]].channel) if codes else "unknown"


def _observations(
    config: GenerationConfig,
    series: SubjectSeries,
    consent: ConsentState,
    dates: Sequence[date],
) -> Iterator[ObservationRow]:
    """Emit consented, available observation rows from the warm-up day onwards.

    An opt-in domain contributes nothing before the day the subject enrolled.
    Backfilling it would hand the engine a baseline the platform never had, and
    would make the "consented recently, cannot yet be scored" path — most of the
    pilot's first month — impossible to reproduce.
    """
    scoreable = consent.scoreable_domains
    warmup = config.warmup_days
    for code, spec in INDICATORS.items():
        if spec.domain not in scoreable:
            continue
        if spec.domain in OBJECTIVE_DOMAINS:
            first_day = warmup
        else:
            first_day = max(warmup, consent.enrolled_on_day)
        mask = series.available[code]
        values = series.indicators[code]
        for day in np.flatnonzero(mask[first_day:]) + first_day:
            index = int(day)
            yield ObservationRow(
                subject_token=series.subject_token,
                indicator_code=code,
                observed_on=dates[index],
                value=format_value(code, float(values[index])),
            )


def _ground_truth_row(
    config: GenerationConfig,
    subject: Subject,
    cohort: Cohort,
    consent: ConsentState,
    series: SubjectSeries,
) -> GroundTruthRow:
    strain = series.latents["distress_strain"]
    return GroundTruthRow(
        subject_token=subject.subject_token,
        cohort=cohort.label(),
        distressed=cohort.distressed,
        gaming=cohort.gaming,
        onset_day=cohort.onset_day,
        onset_on=(
            config.day_to_date(cohort.onset_day).isoformat()
            if cohort.onset_day is not None
            else None
        ),
        ramp_days=cohort.ramp_days,
        severity=cohort.severity,
        strain_at_end=float(strain[-1]),
        deteriorating_at_end=is_deteriorating(strain),
        acute=cohort.acute_day is not None,
        acute_on=(
            config.day_to_date(cohort.acute_day).isoformat()
            if cohort.acute_day is not None
            else None
        ),
        acute_kind=str(cohort.acute_kind) if cohort.acute_kind is not None else None,
        acute_reported=cohort.acute_reported,
        enrolled=consent.enrolled,
        consented_domains=tuple(domain.value for domain in consent.scoreable_domains),
        rank_band=str(subject.rank_band),
        sector_code=subject.sector_code,
        unit_code=subject.unit_code,
        tenure_bucket=str(subject.tenure_bucket),
        language=subject.language,
    )


def observations_by_indicator(
    records: SubjectRecords,
) -> Mapping[str, tuple[tuple[date, float], ...]]:
    """Group a subject's observations by indicator, for the correlation tests."""
    grouped: dict[str, list[tuple[date, float]]] = {}
    for row in records.observations:
        grouped.setdefault(row.indicator_code, []).append((row.observed_on, row.value))
    return {code: tuple(sorted(pairs)) for code, pairs in grouped.items()}
