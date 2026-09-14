"""Accept both the repo capture batch and the SDD CapturePacket shape."""

from __future__ import annotations

from typing import Any

_KIND_FROM_TYPE: dict[str, str] = {
    "bio": "bio",
    "biometric": "bio",
    "voice": "voice",
    "checkin": "checkin",
    "self_assessment": "checkin",
    "journal": "journal",
    "instrument": "instrument",
}


def normalize_capture_payload(body: dict[str, Any]) -> dict[str, Any]:
    """Map ``packet_id`` / ``payload_type`` / ``payload`` onto the live contract."""
    out = dict(body)
    if not out.get("client_batch_id") and out.get("packet_id"):
        out["client_batch_id"] = str(out["packet_id"])
    items = out.get("items")
    if not isinstance(items, list):
        payload = out.get("payload")
        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict):
            items = [payload]
        else:
            items = []
    kind = _KIND_FROM_TYPE.get(str(out.get("payload_type") or "").lower(), "")
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        row = dict(item)
        if not row.get("kind") and kind:
            row["kind"] = kind
        normalized.append(row)
    out["items"] = normalized
    return out
