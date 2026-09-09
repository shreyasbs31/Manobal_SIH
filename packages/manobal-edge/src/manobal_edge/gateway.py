"""Accept a device batch and forward it to Zone 2. Never persist identifiers.

The phone already holds a subject token. This process checks the batch shape
and the packet ceiling, then posts to core ``/v1/ingest/captures``. It has no
route to Zone 3 and no database of its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx

MAX_PACKETS = 500
ALLOWED_KINDS = frozenset({"bio", "voice", "checkin"})
FORBIDDEN_KEYS = frozenset(
    {"service_no", "full_name", "mobile_e164", "name", "aadhaar", "rank_code"}
)


@dataclass(frozen=True, slots=True)
class SyncResult:
    accepted: bool
    status_code: int
    body: dict[str, Any]


class CoreCaptures(Protocol):
    def post_captures(self, payload: dict[str, Any]) -> SyncResult: ...


class HttpCoreCaptures:
    def __init__(self, base_url: str, *, token: str, timeout: float = 5.0) -> None:
        self._url = f"{base_url.rstrip('/')}/v1/ingest/captures"
        self._token = token
        self._timeout = timeout

    def post_captures(self, payload: dict[str, Any]) -> SyncResult:
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(
                self._url,
                json=payload,
                headers={"Authorization": f"Bearer {self._token}"},
            )
        content_type = response.headers.get("content-type", "")
        parsed = response.json() if content_type.startswith("application/json") else {}
        body = parsed if isinstance(parsed, dict) else {}
        return SyncResult(
            accepted=response.is_success, status_code=response.status_code, body=body
        )


class CaptureForwarder:
    def __init__(self, core: CoreCaptures) -> None:
        self._core = core

    def forward(self, payload: dict[str, Any]) -> SyncResult:
        reason = validate_batch(payload)
        if reason is not None:
            return SyncResult(
                accepted=False,
                status_code=422,
                body={"code": "MB-4220", "detail": reason},
            )
        return self._core.post_captures(payload)


def validate_batch(payload: dict[str, Any]) -> str | None:
    if not payload.get("subject_token") or not payload.get("client_batch_id"):
        return "subject_token and client_batch_id are required"
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        return "items must be a non-empty list"
    if len(items) > MAX_PACKETS:
        return "batch exceeds the capture packet ceiling"
    for item in items:
        if not isinstance(item, dict):
            return "each item must be an object"
        if FORBIDDEN_KEYS.intersection(item):
            return "identifying fields are not permitted on the edge"
        if item.get("kind") not in ALLOWED_KINDS:
            return "unknown capture kind"
    return None
