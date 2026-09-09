"""A receipt the person can hold that does not depend on this database."""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.conf import settings

from manobal_core.apps.governance.models import ErasureRequest


def issue_receipt(request: ErasureRequest, *, now: datetime | None = None) -> tuple[str, str]:
    """Return ``(receipt_id, signature)``. The signature is over the receipt body."""
    moment = now or datetime.now(tz=UTC)
    receipt_id = f"rcpt_{uuid4().hex}"
    body = {
        "receipt_id": receipt_id,
        "subject_token": request.subject_token,
        "data_type": request.data_type,
        "completed_at": moment.isoformat(),
        "stores": sorted(request.store_progress),
    }
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(encoded).hexdigest()
    signature = _signing_key().sign(digest.encode())
    return receipt_id, base64.urlsafe_b64encode(signature).decode().rstrip("=")


def _signing_key() -> Ed25519PrivateKey:
    cfg = cast(dict[str, Any], settings.ERASURE_RECEIPT)
    raw = base64.b64decode(str(cfg["PRIVATE_KEY_B64"]))
    return Ed25519PrivateKey.from_private_bytes(raw)
