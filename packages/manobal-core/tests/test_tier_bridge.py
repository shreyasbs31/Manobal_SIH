"""The two ``Tier`` enums must never be compared without conversion.

The engine orders tiers (``min``, ``<``) so it uses an ``IntEnum``. The store
persists and renders them, so it uses text choices. Both are named ``Tier``.
An import swap compiles, runs, and silently denies every officer-visible case:
``2 in {"T2", "T3", "T4"}`` is ``False``.

These tests pin the conversion in both directions against every member of both
enums, so a new tier that is added on one side and forgotten on the other fails
here rather than in production access control.
"""

from __future__ import annotations

import pytest

from manobal_core.apps.governance.enums import (
    MEDICAL_OFFICER_TIERS,
    OFFICER_VISIBLE_TIERS,
)
from manobal_core.apps.governance.enums import Tier as StoredTier
from manobal_core.apps.governance.tiers import to_engine, to_stored
from manobal_risk.types import Tier as EngineTier


class TestTheBridgeIsTotal:
    def test_every_engine_tier_has_a_stored_counterpart(self) -> None:
        assert {member.name for member in EngineTier} == {member.name for member in StoredTier}

    @pytest.mark.parametrize("engine", list(EngineTier))
    def test_round_trip_from_the_engine(self, engine: EngineTier) -> None:
        stored = to_stored(engine)
        assert stored.name == engine.name
        assert to_engine(stored) is engine

    @pytest.mark.parametrize("stored", list(StoredTier))
    def test_round_trip_from_the_store(self, stored: StoredTier) -> None:
        engine = to_engine(stored)
        assert engine.name == stored.name
        assert to_stored(engine) is stored

    def test_an_engine_tier_is_not_silently_usable_as_a_stored_tier(self) -> None:
        """The failure this module exists to prevent. If this assertion ever
        becomes true, the two types have collapsed and the conversion is no
        longer load-bearing — rewrite it rather than delete the test."""
        assert EngineTier.T2 not in OFFICER_VISIBLE_TIERS
        assert to_stored(EngineTier.T2) in OFFICER_VISIBLE_TIERS

    def test_medical_officer_visibility_survives_the_crossing(self) -> None:
        assert to_stored(EngineTier.T2) not in MEDICAL_OFFICER_TIERS
        assert to_stored(EngineTier.T3) in MEDICAL_OFFICER_TIERS
        assert to_stored(EngineTier.T4) in MEDICAL_OFFICER_TIERS
