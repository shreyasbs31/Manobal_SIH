"""Structured JSON logging with request correlation (SDD §10.1).

Every line carries the request id, so a single officer action can be traced
across the API, the Celery worker that scored the assessment and the alert
dispatcher without any of those components logging who the person was.
"""

from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any, Final

#: Context variables rather than thread locals: the ASGI path and Celery's
#: worker pools both make thread identity an unreliable place to hang
#: request-scoped state.
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
actor_id_var: ContextVar[str] = ContextVar("actor_id", default="")
actor_role_var: ContextVar[str] = ContextVar("actor_role", default="")

#: The attributes every LogRecord carries, derived from a throwaway record
#: rather than hardcoded, so a Python release that adds one does not cause it to
#: be emitted as if it were caller-supplied context.
_RESERVED: Final[frozenset[str]] = frozenset(
    logging.LogRecord("", 0, "", 0, "", None, None).__dict__
)


class JsonFormatter(logging.Formatter):
    """Render records as one JSON object per line.

    Note that ``actor_id`` is included but the subject token is not added
    automatically. Correlating an operator's actions is operational telemetry;
    correlating a *subject's* records across every log line would rebuild a
    behavioural profile in the logging system, which is precisely the kind of
    shadow copy the zone model exists to prevent. Where a subject token is
    genuinely needed it must be passed explicitly and deliberately.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if request_id := request_id_var.get():
            payload["request_id"] = request_id
        if actor := actor_id_var.get():
            payload["actor_id"] = actor
        if role := actor_role_var.get():
            payload["actor_role"] = role
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        extras = {k: v for k, v in record.__dict__.items() if k not in _RESERVED}
        payload.update(extras)
        return json.dumps(payload, default=str, ensure_ascii=False)
