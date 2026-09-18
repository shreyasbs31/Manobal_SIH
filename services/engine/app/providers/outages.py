from __future__ import annotations

_FORCED_OPEN: set[str] = set()


def set_forced_outage(provider: str, opened: bool) -> str:
    name = provider.strip().lower()
    if opened:
        _FORCED_OPEN.add(name)
        return "open"
    _FORCED_OPEN.discard(name)
    return "closed"


def is_forced_outage(provider: str) -> bool:
    return provider.strip().lower() in _FORCED_OPEN


def clear_forced_outages() -> None:
    _FORCED_OPEN.clear()
