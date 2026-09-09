"""Missingness and consent must produce the coverage variation they claim to.

Appendix A.3 asks for missingness that is *per-domain and uneven*, because that
is what actually exercises coverage renormalisation. Uniform dropout would leave
every domain equally covered and the renormalisation branch in SDD §4.5 step 4
would never execute against this corpus.

Consent is checked the same way and for the same reason: the interesting case is
not "nobody consented", it is a force where the objective domains are complete
for everybody and the opt-in domains are complete for a minority.
"""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from manobal_synth import GenerationConfig, build_dataset
from manobal_synth.config import ConsentProfile, MissingnessProfile
from manobal_synth.indicators import INDICATORS, OBJECTIVE_DOMAINS

OPT_IN_DOMAINS = ("D4_physiological", "D5_self_report", "D6_vocal_acoustic", "D7_engagement")


def _config(**overrides: object) -> GenerationConfig:
    base = {
        "seed": 808,
        "personnel": 90,
        "duration_days": 240,
        "distress_cohort": 0.2,
        "gaming_cohort": 0.05,
    }
    return GenerationConfig(**{**base, **overrides})  # type: ignore[arg-type]


def _coverage_by_domain(config: GenerationConfig) -> Mapping[str, float]:
    """Rows present as a fraction of rows possible, per domain, over the corpus."""
    present: dict[str, int] = {}
    possible: dict[str, int] = {}
    for records in build_dataset(config).iter_subjects():
        consented = set(records.ground_truth.consented_domains)
        for spec in INDICATORS.values():
            domain = str(spec.domain)
            if domain not in consented:
                continue
            possible[domain] = possible.get(domain, 0) + config.duration_days
        for row in records.observations:
            domain = str(INDICATORS[row.indicator_code].domain)
            present[domain] = present.get(domain, 0) + 1
    return {
        domain: present.get(domain, 0) / (count / len(_codes_in(domain)))
        for domain, count in possible.items()
    }


def _codes_in(domain: str) -> tuple[str, ...]:
    return tuple(code for code, spec in INDICATORS.items() if str(spec.domain) == domain)


def test_no_missingness_gives_near_complete_objective_coverage() -> None:
    coverage = _coverage_by_domain(
        _config(missingness=MissingnessProfile.NONE, consent_profile=ConsentProfile.FULL)
    )
    for domain in OBJECTIVE_DOMAINS:
        assert coverage[str(domain)] > 0.98


def test_realistic_missingness_removes_rows() -> None:
    complete = _coverage_by_domain(
        _config(missingness=MissingnessProfile.NONE, consent_profile=ConsentProfile.FULL)
    )
    sparse = _coverage_by_domain(
        _config(missingness=MissingnessProfile.REALISTIC, consent_profile=ConsentProfile.FULL)
    )
    assert sparse["D1_workload"] < complete["D1_workload"]
    assert sparse["D4_physiological"] < complete["D4_physiological"]


def test_missingness_is_uneven_across_domains() -> None:
    """The property that makes coverage renormalisation worth testing."""
    coverage = _coverage_by_domain(
        _config(missingness=MissingnessProfile.REALISTIC, consent_profile=ConsentProfile.FULL)
    )
    spread = max(coverage.values()) - min(coverage.values())
    assert spread > 0.25, f"missingness is nearly uniform across domains: {coverage}"


def test_wearable_and_hrms_gaps_have_different_shapes() -> None:
    """Wearable non-wear clusters; HRMS outages hit whole units at once.

    Two mechanisms rather than one, because a coverage rule tuned against
    independent day-by-day dropout behaves differently against multi-day blocks.
    """
    config = _config(missingness=MissingnessProfile.REALISTIC, consent_profile=ConsentProfile.FULL)
    dataset = build_dataset(config)
    assert dataset.hrms_outages.any(), "no HRMS outage in the run"

    subjects = list(dataset.iter_subjects())
    worn = subjects[0].series.missingness.wearable_worn
    transitions = int((worn[1:] != worn[:-1]).sum())
    assert 0 < transitions < len(worn) // 2, "non-wear looks like independent coin flips"


@pytest.mark.parametrize("domain", OPT_IN_DOMAINS)
def test_realistic_consent_leaves_opt_in_domains_partially_covered(domain: str) -> None:
    config = _config(
        consent_profile=ConsentProfile.REALISTIC,
        missingness=MissingnessProfile.REALISTIC,
        enrolment_rate=0.42,
    )
    granted = sum(
        1
        for records in build_dataset(config).iter_subjects()
        if domain in records.ground_truth.consented_domains
    )
    share = granted / config.personnel
    assert 0.0 < share < 0.9, f"{domain} consent share {share:.2f} is not partial"


def test_objective_domains_are_never_withheld() -> None:
    config = _config(consent_profile=ConsentProfile.REALISTIC, enrolment_rate=0.05)
    for records in build_dataset(config).iter_subjects():
        consented = set(records.ground_truth.consented_domains)
        assert {str(domain) for domain in OBJECTIVE_DOMAINS} <= consented


def test_a_force_where_nobody_enrols_still_yields_objective_rows() -> None:
    """The degenerate case, expressed as a zero enrolment rate.

    "Nobody consents" is a rate, not a separate profile: the profile decides how
    people choose among the opt-in domains, and the rate decides how many people
    opt in at all. Objective org-store rows still exist because they come from
    records the force already holds — which is exactly why the SDD treats them
    as a distinct legal basis from the opt-in domains.
    """
    config = _config(consent_profile=ConsentProfile.REALISTIC, enrolment_rate=0.0)
    for records in build_dataset(config).iter_subjects():
        assert not records.ground_truth.enrolled
        assert records.observations
        emitted = {str(INDICATORS[row.indicator_code].domain) for row in records.observations}
        assert emitted <= {str(domain) for domain in OBJECTIVE_DOMAINS}


def test_consent_rows_record_declines_as_well_as_grants() -> None:
    config = _config(consent_profile=ConsentProfile.REALISTIC, enrolment_rate=0.42)
    rows = [row for rec in build_dataset(config).iter_subjects() for row in rec.consent]
    assert any(row.granted for row in rows)
    assert any(not row.granted for row in rows)
    assert all(row.requires_opt_in or row.granted for row in rows)
