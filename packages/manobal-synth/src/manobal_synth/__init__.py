"""MANOBAL causal synthetic data generator (SDD Appendix A.3).

A first-class deliverable rather than a test fixture. Public datasets validate
the *methods* the risk engine uses; they cannot exercise the *system*. This
package produces a corpus that can: eighty thousand personnel over eighteen
months, generated in causal order so that the multi-domain correlations the
corroboration gate is supposed to detect actually exist in the data, with
injected ground truth so that false positives and false negatives (SDD §10.6
K3/K4) are arithmetic rather than opinion.

Four properties are load-bearing.

*Causal order.* Deployment drives workload, workload drives sleep, sleep drives
HRV and mood, mood drives leave-seeking and withdrawal. See ``chain.py``, where
the graph is written out as one function; the correlations are consequences of it
and are nowhere injected directly.

*Personal baselines.* Every subject has their own level and their own dispersion
for every primitive. A person who has always worked long hours does not look
distressed, which is the modelling claim SDD §4.4 rests the whole
baseline-of-one approach on.

*Partial consent and shaped missingness.* Three domains come from records the
force already holds and need no opt-in; four are declined separately, and each
fails in its own shape. That asymmetry is what exercises coverage
renormalisation.

*Determinism.* The same seed yields byte-identical output. Every draw comes from
a label-addressed substream, so a subject generated alone in a test is identical
to the same subject generated in the middle of a run of eighty thousand.
"""

from __future__ import annotations

from .chain import SubjectSeries, generate_subject_series
from .cohorts import Cohort, assign_cohorts
from .config import (
    ConsentProfile,
    DeploymentModel,
    DistressOnset,
    FairnessProfile,
    GenerationConfig,
    MissingnessProfile,
    OutputFormat,
    RankDistribution,
)
from .consent import ConsentState, assign_consent
from .dataset import Dataset, SubjectRecords, build_dataset
from .errors import ManobalSynthError, SynthConfigError
from .indicators import INDICATORS, OBJECTIVE_DOMAINS, Channel
from .person import PersonModel, build_person
from .population import PostingClass, RankBand, Subject, TenureBucket, Unit
from .records import (
    AcuteTriggerRow,
    ConsentRow,
    GroundTruthRow,
    IncidentRow,
    ObservationRow,
    SubjectRow,
    UnitRow,
)
from .version import GENERATOR_VERSION
from .writer import Manifest, write_dataset

__version__ = GENERATOR_VERSION

__all__ = [
    "GENERATOR_VERSION",
    "INDICATORS",
    "OBJECTIVE_DOMAINS",
    "AcuteTriggerRow",
    "Channel",
    "Cohort",
    "ConsentProfile",
    "ConsentRow",
    "ConsentState",
    "Dataset",
    "DeploymentModel",
    "DistressOnset",
    "FairnessProfile",
    "GenerationConfig",
    "GroundTruthRow",
    "IncidentRow",
    "Manifest",
    "ManobalSynthError",
    "MissingnessProfile",
    "ObservationRow",
    "OutputFormat",
    "PersonModel",
    "PostingClass",
    "RankBand",
    "RankDistribution",
    "Subject",
    "SubjectRecords",
    "SubjectRow",
    "SubjectSeries",
    "SynthConfigError",
    "TenureBucket",
    "Unit",
    "UnitRow",
    "assign_cohorts",
    "assign_consent",
    "build_dataset",
    "build_person",
    "generate_subject_series",
    "write_dataset",
]
