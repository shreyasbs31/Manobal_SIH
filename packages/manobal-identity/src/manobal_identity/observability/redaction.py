"""Log redaction for the identity enclave.

Zone 2 redacts logs because a stray score or journal line would be a privacy
incident. Zone 3 redacts for a starker reason: this is the one process that
holds names, service numbers and mobile numbers in memory at all, and a log line
is the easiest way for them to end up somewhere with weaker access controls than
the vault — a log aggregator, a terminal scrollback, a support ticket.

The filter is deliberately blunt. It drops anything whose key looks identifying,
and it drops decrypted plaintext regardless of key. Over-redaction costs a
debugging session; under-redaction costs a disclosure notification under §11.4.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Final

IDENTIFYING_KEYS: Final = frozenset(
    {
        "service_no",
        "service_number",
        "full_name",
        "name",
        "rank_code",
        "rank",
        "mobile",
        "mobile_e164",
        "phone",
        "contact",
        "plaintext",
        "data_key",
        "kek",
        "index_key",
        "secret",
        "password",
        "wrapped_key",
    }
)

REDACTED: Final = "[redacted]"

_SERVICE_NO_SHAPE: Final = re.compile(
    r"\b[A-Z]{2,6}[-/\s]?\d{4}[-/\s]?\d{4,8}\b", re.IGNORECASE
)
"""Catches a service number pasted into a free-text message, where no key name
gives it away."""

_MOBILE_SHAPE: Final = re.compile(r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b")


class VaultRedactionFilter(logging.Filter):
    """Scrubs identifying material from records before they reach a handler."""

    def filter(self, record: logging.LogRecord) -> bool:
        for attribute, value in list(vars(record).items()):
            if attribute.startswith("_"):
                continue
            if attribute in {"msg", "args"} or attribute not in _RESERVED:
                setattr(record, attribute, _scrub(attribute, value))
        return True


def _scrub(key: str, value: Any) -> Any:
    """Return a redacted copy. Never mutates the caller's object."""
    if key.lower() in IDENTIFYING_KEYS:
        return REDACTED
    if isinstance(value, str):
        return _MOBILE_SHAPE.sub(REDACTED, _SERVICE_NO_SHAPE.sub(REDACTED, value))
    if isinstance(value, dict):
        return {k: _scrub(str(k), v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return type(value)(_scrub(key, item) for item in value)
    return value


_RESERVED: Final = frozenset(
    set(vars(logging.LogRecord("", 0, "", 0, "", None, None)))
    | {"message", "asctime", "taskName"}
)
"""Standard LogRecord attributes, which carry no payload of ours."""
