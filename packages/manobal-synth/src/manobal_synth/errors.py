"""Exception hierarchy for the generator.

One root so that the CLI can catch everything the library raises deliberately
and turn it into an exit code, without swallowing programming errors.
"""

from __future__ import annotations


class ManobalSynthError(Exception):
    """Base class for every error this package raises on purpose."""


class SynthConfigError(ManobalSynthError):
    """A generation parameter is outside the range the generator can honour.

    Raised at construction time rather than mid-run: a 40-minute generation that
    fails on the last subject because a rate was negative is a worse outcome than
    a refusal in the first millisecond.
    """
