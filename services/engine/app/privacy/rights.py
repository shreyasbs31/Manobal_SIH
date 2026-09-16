from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from ..scoring.ruleset import load_private

PURGED: dict[str, set[str]] = {}
RECEIPTS: list[dict[str, Any]] = []
KILLSWITCHES = {
    "agent": False,
    "voice": False,
    "copilot": False,
    "briefs": False,
    "alerts_t2_t3": False,
    "forecast": False,
    "jitai": False,
}
TREND_REQUESTS: list[dict[str, str]] = []
BREAKGLASS: list[dict[str, str]] = []
GRANTS_NEEDING_NOTE: list[dict[str, str]] = []


def purge(token: str, data_type: str, row_count: int) -> dict[str, Any]:
    PURGED.setdefault(token, set()).add(data_type)
    payload = f"{token}:{data_type}:{row_count}".encode()
    digest = hashlib.sha256(payload).hexdigest()
    signature = load_private("wdec1").sign(payload)
    receipt = {
        "token": token,
        "data_type": data_type,
        "row_count": row_count,
        "sha256": digest,
        "signature": signature.hex(),
        "at": datetime.now(UTC).isoformat(),
    }
    RECEIPTS.append(receipt)
    return receipt


def set_killswitch(name: str, enabled: bool, actor: str) -> None:
    if name == "acute":
        raise ValueError("acute path cannot be switched off")
    if name not in KILLSWITCHES:
        raise KeyError(name)
    KILLSWITCHES[name] = enabled
    del actor


def request_trend_share(case_id: str, token: str, domain: str) -> dict[str, str]:
    row = {"case_id": case_id, "token": token, "domain": domain, "status": "pending"}
    TREND_REQUESTS.append(row)
    return row


def decide_trend_share(case_id: str, domain: str, status: str) -> None:
    for row in TREND_REQUESTS:
        if row["case_id"] == case_id and row["domain"] == domain:
            row["status"] = status


def break_glass(
    *, actor: str, approver: str, target_token: str, justification: str
) -> dict[str, str]:
    if not approver or approver == actor:
        raise ValueError("approver_required")
    if len(justification) < 8:
        raise ValueError("justification")
    row = {
        "actor": actor,
        "approver": approver,
        "target_token": target_token,
        "justification": justification,
        "wdec_review_status": "pending",
    }
    BREAKGLASS.append(row)
    return row


def contact_note_due(grant_id: str, due_iso: str) -> None:
    GRANTS_NEEDING_NOTE.append({"grant_id": grant_id, "due": due_iso, "note": ""})


def write_contact_note(grant_id: str, note: str) -> None:
    for row in GRANTS_NEEDING_NOTE:
        if row["grant_id"] == grant_id:
            row["note"] = note


def revoke_if_note_missing(grant_id: str) -> bool:
    return any(row["grant_id"] == grant_id and not row["note"] for row in GRANTS_NEEDING_NOTE)


def zone_x_terms() -> tuple[str, ...]:
    return ("APPRAISAL", "PROMOTION", "DISCIPLINARY", "MEDICAL_CATEGORY", "POSTING_DECISION")
