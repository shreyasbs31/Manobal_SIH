"""Characterisation of the withdrawal-dilution effect in the SDD §4.5 formula.

**This file documents a live design question, not a passing feature.** It is
written as a characterisation test — it pins down what the specified formula
actually does today so that the behaviour is visible in CI rather than
discovered in a pilot, and so that any future change to it is a deliberate one.

The effect
----------
The composite is a coverage-renormalised weighted *mean*:

    WSI = sum_{d in A} w_d * Z_d / sum_{d in A} w_d

A domain in which a subject is doing well pulls that mean down. Withdrawing
consent for such a domain removes it from ``A``, which raises the mean. The tier
can therefore *rise* as a direct consequence of withdrawing consent.

Why it matters
--------------
SDD §7.7 promises "withdrawal without friction — one screen, no justification,
no notification to anyone, immediate effect". If withdrawing wearable consent can
turn a private T1 into a T3 with an immediate push to the welfare officer, then
withdrawal is not frictionless: it is a gamble, and the first person it happens
to will tell their unit that turning the wearable off got them reported. That is
precisely the trust failure K10 measures and §12.3 P2 warns about.

Options, for the record
-----------------------
1. Accept and disclose it in the consent text. Cheapest, and honest, but it makes
   the withdrawal screen frightening.
2. Recompute on withdrawal and suppress any tier *increase* attributable solely
   to reduced coverage, for a defined settling period. Belongs in the service
   layer, since the engine is stateless and cannot see a withdrawal event.
3. Replace the mean with a coverage-renormalised quantile or a max-of-domains
   rule, so a benign domain never dilutes an adverse one. Changes the calibration
   of every threshold in the ruleset.

Until that decision is made, the tests below assert current behaviour.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from manobal_risk import score, score_with_trace
from manobal_risk.ruleset import Ruleset
from manobal_risk.types import Domain, Tier

from .builders import build_history

ASSESSED_AT = datetime(2026, 6, 30, 2, 0, tzinfo=UTC)

#: A jawan whose duty and leave patterns have both deviated sharply, but whose
#: wearable and self-report signals are steady. Two domains breach, so the
#: corroboration gate is satisfied — but the two calm domains drag the mean below
#: the T2 boundary, so nobody is told.
ADVERSE = {Domain.WORKLOAD: 0.9, Domain.LEAVE: 0.9}
CALM = {Domain.PHYSIOLOGICAL: 0.0, Domain.SELF_REPORT: 0.0}


class TestWithdrawalCanRaiseATier:
    def test_the_subject_is_invisible_while_sharing_everything(
        self, ruleset: Ruleset
    ) -> None:
        result = score(
            build_history(ruleset, ADVERSE | CALM), ruleset, assessed_at=ASSESSED_AT
        )

        assert result.corroborated is True
        assert result.tier is Tier.T1
        assert result.is_actionable_by_officer is False

    def test_withdrawing_the_calm_domains_raises_the_subject_to_high(
        self, ruleset: Ruleset
    ) -> None:
        """The finding, stated as bluntly as it deserves: this subject's
        behaviour did not change. They turned off their wearable and stopped
        answering questionnaires, and that alone moved them from a private T1 to
        a T3 with an immediate push to their welfare officer."""
        result = score(
            build_history(
                ruleset, ADVERSE | CALM, consented_domains=frozenset(ADVERSE)
            ),
            ruleset,
            assessed_at=ASSESSED_AT,
        )

        assert result.tier is Tier.T3
        assert result.is_actionable_by_officer is True

    def test_the_mechanism_is_dilution_not_a_change_in_corroboration(
        self, ruleset: Ruleset
    ) -> None:
        """Both assessments corroborate on exactly the same two domains. The only
        thing that moved is the denominator of the mean."""
        _, sharing = score_with_trace(
            build_history(ruleset, ADVERSE | CALM), ruleset, assessed_at=ASSESSED_AT
        )
        _, withdrawn = score_with_trace(
            build_history(ruleset, ADVERSE | CALM, consented_domains=frozenset(ADVERSE)),
            ruleset,
            assessed_at=ASSESSED_AT,
        )

        assert set(sharing.breaching_domains) == set(withdrawn.breaching_domains)
        assert sharing.wsi == pytest.approx(0.4068, abs=1e-3)
        assert withdrawn.wsi == pytest.approx(0.9, abs=1e-9)


class TestTheConverseAlsoHolds:
    def test_opting_in_to_a_calm_domain_can_lower_a_tier(self, ruleset: Ruleset) -> None:
        """The same arithmetic read the other way, and the reason this is a real
        design question rather than a rounding artefact: sharing more data is a
        way to *reduce* your tier, which is an incentive the system should be
        deliberate about creating."""
        withdrawn = score(
            build_history(ruleset, ADVERSE | CALM, consented_domains=frozenset(ADVERSE)),
            ruleset,
            assessed_at=ASSESSED_AT,
        )
        sharing = score(
            build_history(ruleset, ADVERSE | CALM), ruleset, assessed_at=ASSESSED_AT
        )

        assert withdrawn.tier > sharing.tier
