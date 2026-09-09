"""Risk-engine exceptions.

The engine fails loudly. There is no code path that scores a subject against a
ruleset it could not verify, and no path that silently substitutes a default for
a malformed rule. A safety-critical component that guesses is worse than one
that refuses to start.
"""

from __future__ import annotations


class ManobalRiskError(Exception):
    """Base class for every error raised by the risk engine."""


class RulesetError(ManobalRiskError):
    """The ruleset artefact is malformed, internally inconsistent, or unusable."""


class RulesetSignatureError(RulesetError):
    """The ruleset artefact's signature is missing or does not verify.

    Raised at load time so the service refuses to start rather than scoring
    against unapproved rules (SDD §10.5).
    """


class InsufficientBaselineError(ManobalRiskError):
    """A baseline was requested for a window with too few observations."""
