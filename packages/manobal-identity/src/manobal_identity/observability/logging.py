"""Structured logging for the identity enclave.

A near-copy of the Zone 2 formatter, kept separate on purpose: importing it
would pull ``manobal_core`` into the enclave's image. See the note in
``settings.base.LOGGING``.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Final


class JsonFormatter(logging.Formatter):
    """One JSON object per line, with the request correlation fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "zone": 3,
        }
        for attribute, value in vars(record).items():
            if attribute not in _RESERVED and not attribute.startswith("_"):
                payload[attribute] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


_RESERVED: Final = frozenset(
    set(vars(logging.LogRecord("", 0, "", 0, "", None, None)))
    | {"message", "asctime", "taskName"}
)
