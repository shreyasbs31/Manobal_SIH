from __future__ import annotations

import logging
import re
from collections.abc import Mapping, Sequence
from typing import cast

import structlog
from structlog.typing import Processor

type LogScalar = str | int | float | bool | None
type LogValue = LogScalar | list[LogValue] | dict[str, LogValue]

REDACTED = "[redacted]"
PII_KEYS = frozenset(
    {
        "name",
        "full_name",
        "service_no",
        "service_number",
        "phone",
        "phone_number",
        "posting",
        "address",
        "nominee_name",
        "contact",
        "request_body",
        "body",
    }
)
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)")
SERVICE_PATTERN = re.compile(r"\b(?:SYN|SERVICE)[-_ ]?[A-Z0-9]{4,}\b", re.IGNORECASE)


def _redact_value(key: str, value: object) -> LogValue:
    if key.lower() in PII_KEYS:
        return REDACTED
    if isinstance(value, Mapping):
        return {
            str(nested_key): _redact_value(str(nested_key), nested_value)
            for nested_key, nested_value in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_redact_value("", item) for item in value]
    if isinstance(value, str):
        return SERVICE_PATTERN.sub(
            REDACTED,
            PHONE_PATTERN.sub(REDACTED, value),
        )
    if value is None or isinstance(value, (int, float, bool)):
        return value
    return str(value)


def redact_pii(
    _logger: object,
    _method_name: str,
    event_dict: dict[str, object],
) -> dict[str, LogValue]:
    return {key: _redact_value(key, value) for key, value in event_dict.items()}


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            cast(Processor, redact_pii),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
