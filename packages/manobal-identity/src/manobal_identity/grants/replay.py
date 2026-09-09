"""Single-use enforcement for grant assertions.

An assertion is a bearer capability. Without a replay guard, an assertion
captured once — from a log, a proxy, a crash dump — resolves the same person
again and again, and only the first resolution ever looked like it needed
authorisation. Making each assertion single-use turns "who may resolve" into
"how many times, exactly", which is what the audit trail claims to record.

Two implementations: an in-memory guard for tests and single-process use, and a
database-backed guard in :mod:`manobal_identity.apps.vault.models` for the real
service, where two resolver replicas must not each honour the same assertion.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class ReplayGuard(Protocol):
    """Records spent assertion identifiers."""

    def consume(self, assertion_id: str, expires_at: datetime, now: datetime) -> bool:
        """Claim ``assertion_id`` as at ``now``.

        Returns ``True`` if this caller claimed it first, ``False`` if it had
        already been spent. Implementations must make this atomic; a check
        followed by a separate write is a race two replicas will lose.

        ``now`` is supplied by the caller rather than read from the clock so
        that the guard and the expiry checks that precede it agree on what time
        it is. A guard consulting its own clock can expire an entry the verifier
        still considers live, which reopens the replay window it exists to shut.
        """


class InMemoryReplayGuard:
    """Process-local guard. Correct for tests, insufficient for two replicas."""

    def __init__(self) -> None:
        self._spent: dict[str, datetime] = {}

    def consume(self, assertion_id: str, expires_at: datetime, now: datetime) -> bool:
        self._evict(now)
        if assertion_id in self._spent:
            return False
        self._spent[assertion_id] = expires_at
        return True

    def _evict(self, now: datetime) -> None:
        """Forget assertions that could no longer be replayed anyway.

        An expired assertion is refused on its expiry, so retaining it proves
        nothing and grows without bound.
        """
        self._spent = {
            key: expiry for key, expiry in self._spent.items() if expiry > now
        }
