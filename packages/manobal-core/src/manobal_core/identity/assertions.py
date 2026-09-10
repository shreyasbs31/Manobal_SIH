"""Sign an ``mbga1`` grant assertion. Duplicated from Zone 3 on purpose.

The wire format must match ``manobal_identity.grants.assertion`` byte-for-byte.
This module does not import that package: sharing the signer would put vault
types on this side of the air-gap.
"""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta
from typing import Any, Final, cast
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.conf import settings

from manobal_core.apps.authz.principal import Principal
from manobal_core.apps.governance.models import AccessGrant, Case

FORMAT_PREFIX: Final = "mbga1"
MAX_ASSERTION_LIFETIME: Final = timedelta(minutes=5)


def sign_resolve_assertion(
    *,
    case: Case,
    grant: AccessGrant,
    principal: Principal,
    now: datetime | None = None,
) -> str:
    """Sign a five-minute resolve assertion for ``grant``."""
    return sign_grant_assertion(
        case=case,
        grant=grant,
        principal=principal,
        operation="resolve",
        purpose="acute_response",
        now=now,
    )


def sign_grant_assertion(
    *,
    case: Case,
    grant: AccessGrant,
    principal: Principal,
    operation: str,
    purpose: str,
    second_approver_id: str | None = None,
    now: datetime | None = None,
) -> str:
    """Sign a five-minute grant assertion. Wire format matches Zone 3."""
    moment = now or datetime.now(tz=UTC)
    cfg = cast(dict[str, Any], settings.GRANT_ASSERTION)
    payload = {
        "assertion_id": f"ga_{uuid4().hex}",
        "key_id": str(cfg["KEY_ID"]),
        "issuer": str(cfg["ISSUER"]),
        "issued_at": moment.isoformat(),
        "expires_at": (moment + MAX_ASSERTION_LIFETIME).isoformat(),
        "operation": operation,
        "grant_id": str(grant.id),
        "grant_expires_at": grant.expires_at.astimezone(UTC).isoformat(),
        "case_id": str(case.id),
        "subject_token": case.subject_token,
        "purpose": purpose,
        "actor_id": principal.actor_id,
        "actor_role": principal.role,
        "actor_unit_code": principal.unit_code or "",
        "actor_force_code": principal.force_code,
        "second_approver_id": second_approver_id,
    }
    encoded = _b64(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
    body = f"{FORMAT_PREFIX}.{encoded}"
    signature = _signing_key(cfg).sign(body.encode())
    return f"{body}.{_b64(signature)}"


def _signing_key(cfg: dict[str, Any]) -> Ed25519PrivateKey:
    raw = base64.b64decode(str(cfg["PRIVATE_KEY_B64"]))
    return Ed25519PrivateKey.from_private_bytes(raw)


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")
