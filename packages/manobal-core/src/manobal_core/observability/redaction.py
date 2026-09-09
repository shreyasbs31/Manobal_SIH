"""Structural redaction of sensitive values from application logs (SDD §10.1).

The threat is mundane and therefore likely: someone adds
``logger.info("scoring %s", payload)`` while debugging, the payload contains a
service number and a PHQ-9 total, and six months later that line is in a log
aggregator that a dozen operators can search. No amount of review reliably
catches every instance, so this filter drops or masks the values at the logging
boundary instead of relying on discipline.

Two deliberate design choices:

* **Deny by key, not by value.** Trying to recognise a service number by its
  shape produces both false negatives and a regex that scans every log line.
  Matching on well-known key names is cheap and predictable.
* **Fail closed on structured payloads.** An unrecognised object passed as a
  log argument is replaced with its type name rather than repr'd, because a
  repr of a Django model instance will happily print every field it holds.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Final

#: Key names whose values must never appear in a log line. Matched
#: case-insensitively against dictionary keys and ``key=value`` fragments.
SENSITIVE_KEYS: Final[frozenset[str]] = frozenset(
    {
        # Direct identifiers — Zone 3 material that must not reach Zone 2 logs.
        "service_number",
        "service_no",
        "svc_no",
        "name",
        "full_name",
        "father_name",
        "mobile",
        "phone",
        "email",
        "aadhaar",
        "dob",
        "date_of_birth",
        "address",
        # Clinical and self-report content.
        "journal",
        "journal_text",
        "entry_text",
        "transcript",
        "utterance",
        "message",
        "responses",
        "item_responses",
        "phq9",
        "gad7",
        "total_score",
        "subscales",
        # Engine internals. FR-3.7 keeps the number inside the engine, and a log
        # line is a way out of the engine.
        "wsi",
        "welfare_signal_index",
        "deviation",
        "domain_scores",
        "raw_score",
        # Credentials.
        "password",
        "secret",
        "token_secret",
        "authorization",
        "api_key",
        "private_key",
        "client_secret",
        "signature",
    }
)

REDACTED: Final = "[redacted]"

#: ``key=value`` and ``"key": "value"`` fragments inside an already-formatted
#: string. A second line of defence for messages built before they reach here.
_INLINE = re.compile(
    r"(?i)\b(" + "|".join(re.escape(k) for k in sorted(SENSITIVE_KEYS)) + r")\b"
    r"(\s*[:=]\s*)"
    r"(\"[^\"]*\"|'[^']*'|[^\s,;}\)]+(?:\s+(?![A-Za-z_][\w]*[:=])[^\s,;}\)]+)*)"
)

#: Depth limit for recursive scrubbing. A cyclic or pathologically nested
#: structure in a log call should not become a stack overflow in the logger.
_MAX_DEPTH: Final = 6


def _is_sensitive(key: object) -> bool:
    return isinstance(key, str) and key.strip().lower().lstrip("_") in SENSITIVE_KEYS


def scrub(value: Any, *, depth: int = 0) -> Any:
    """Return ``value`` with sensitive content removed.

    Containers are rebuilt rather than mutated, so scrubbing a log argument can
    never alter the caller's data — a logger that changed the object it was
    asked to print would be a spectacular class of bug.
    """
    if depth >= _MAX_DEPTH:
        return f"<{type(value).__name__}>"
    if isinstance(value, dict):
        return {
            key: (REDACTED if _is_sensitive(key) else scrub(item, depth=depth + 1))
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        scrubbed = [scrub(item, depth=depth + 1) for item in value]
        return type(value)(scrubbed) if not isinstance(value, set) else set(scrubbed)
    if isinstance(value, str):
        return _INLINE.sub(rf"\1\2{REDACTED}", value)
    if isinstance(value, (int, float, bool, type(None))):
        return value
    # Anything else — model instances, dataclasses, exceptions carrying payloads
    # — is summarised rather than rendered. Its repr is not worth the risk.
    return f"<{type(value).__name__}>"


class RedactionFilter(logging.Filter):
    """Scrub every record passing through a handler.

    Installed as a filter rather than a formatter so it applies regardless of
    which formatter a handler uses, including handlers added later by an
    operator who has not read this module.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = scrub(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = scrub(record.args)
            else:
                record.args = tuple(scrub(arg) for arg in record.args)
        for attr in ("payload", "detail", "context", "extra"):
            if hasattr(record, attr):
                setattr(record, attr, scrub(getattr(record, attr)))
        return True
