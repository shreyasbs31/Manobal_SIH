"""The one sanctioned crossing between the engine's tier and the store's tier.

Two enums in this system are called ``Tier`` and they are not the same type:

===========================  ==========  ==============================
Type                         Kind        ``Tier.T2`` is
===========================  ==========  ==============================
``manobal_risk.types.Tier``  ``IntEnum`` ``2``
``governance.enums.Tier``    Text choice ``"T2"``
===========================  ==========  ==============================

Both are right for their own side. The engine compares and orders tiers —
``min(raw_tier, Tier.T1)`` for the corroboration gate, ``final < previous`` for
hysteresis — and an ``IntEnum`` makes that read as the spec writes it. The store
persists them and renders them, where an opaque ``2`` in a database column is a
gift to nobody.

What makes this dangerous is that they share a name, so an import swap produces
code that runs. ``2 in {"T2", "T3", "T4"}`` is ``False``, silently: an
access-control check fed an engine tier does not raise, it *denies*, and a
system that quietly stops showing officers their T3 cases fails in the direction
nobody files a bug about.

So the conversion is explicit, it lives in one place, and it is tested against
every member of both enums rather than the handful someone thought of.
"""

from __future__ import annotations

from manobal_risk.types import Tier as EngineTier

from .enums import Tier as StoredTier

_TO_STORED: dict[EngineTier, StoredTier] = {
    EngineTier.T0: StoredTier.T0,
    EngineTier.T1: StoredTier.T1,
    EngineTier.T2: StoredTier.T2,
    EngineTier.T3: StoredTier.T3,
    EngineTier.T4: StoredTier.T4,
}

_TO_ENGINE: dict[StoredTier, EngineTier] = {v: k for k, v in _TO_STORED.items()}


def to_stored(tier: EngineTier) -> StoredTier:
    """Convert an engine tier into the form the governance store persists."""
    try:
        return _TO_STORED[tier]
    except KeyError as exc:  # pragma: no cover — unreachable while both enums agree
        raise ValueError(
            f"No stored tier corresponds to engine tier {tier!r}. The two "
            f"enums have diverged; see manobal_core.apps.governance.tiers."
        ) from exc


def to_engine(tier: StoredTier) -> EngineTier:
    """Convert a stored tier back into the ordered form the engine compares."""
    try:
        return _TO_ENGINE[tier]
    except KeyError as exc:  # pragma: no cover — unreachable while both enums agree
        raise ValueError(
            f"No engine tier corresponds to stored tier {tier!r}. The two "
            f"enums have diverged; see manobal_core.apps.governance.tiers."
        ) from exc
