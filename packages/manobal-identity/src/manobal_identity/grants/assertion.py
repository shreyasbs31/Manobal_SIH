"""Signed capability assertions carrying a grant across the zone boundary.

§4.9 requires that every resolution be backed by a live, purposeful, attributed
case grant. The grants themselves live in ``gov_store``, in Zone 2. The enclave
that must honour them lives in Zone 3 and is forbidden a route back — §3.2 is
unambiguous that the isolation is structural, not a matter of good behaviour.

The resolution is to move the proof rather than the query. Zone 2 signs a
short-lived statement of the grant's existence and terms; Zone 3 verifies the
signature and enforces the terms. Authority stays where the data is, the
boundary stays closed, and an officer cannot manufacture their own permission
because the signing key is not theirs to hold.

**On the wire format.** This is not a JWT, and that is deliberate. JWT's
algorithm agility has produced a long line of ``alg: none`` and RS256/HS256
confusion failures, all of which come from letting the token tell the verifier
how to check it. Here the algorithm is Ed25519, fixed in the format prefix and
not negotiable. A token that wants to be verified differently is simply
malformed.
"""

from __future__ import annotations

import base64
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Final

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from manobal_identity.grants.replay import ReplayGuard

FORMAT_PREFIX: Final = "mbga1"
"""MANOBAL grant assertion, version 1, Ed25519. Not negotiable."""

MAX_ASSERTION_LIFETIME: Final = timedelta(minutes=5)
"""A capability is a bearer credential. It should be worth stealing for as
short a time as possible, and no legitimate resolve needs longer."""

CLOCK_SKEW_TOLERANCE: Final = timedelta(seconds=30)
"""Zone 2 and Zone 3 are separate hosts on separate VLANs with separate clocks.
Refusing a T4 resolution over a few seconds of NTP drift would be a safety
failure dressed up as a security control."""


class Operation(StrEnum):
    """What the assertion authorises. Distinct scopes, per §4.9."""

    RESOLVE = "resolve"
    BREAK_GLASS = "break_glass"


class RejectionReason(StrEnum):
    """Why an assertion was refused.

    Machine-readable because every refusal is audited and the audit is queried
    by reason — a spike in ``BAD_SIGNATURE`` is a different incident from a
    spike in ``GRANT_EXPIRED``.
    """

    MALFORMED = "MB-3001"
    UNKNOWN_KEY = "MB-3002"
    BAD_SIGNATURE = "MB-3003"
    ASSERTION_EXPIRED = "MB-3004"
    NOT_YET_VALID = "MB-3005"
    LIFETIME_TOO_LONG = "MB-3006"
    GRANT_EXPIRED = "MB-3007"
    REPLAYED = "MB-3008"
    OPERATION_MISMATCH = "MB-3009"
    SECOND_APPROVER_MISSING = "MB-3010"
    SECOND_APPROVER_IS_ACTOR = "MB-3011"
    UNEXPECTED_SECOND_APPROVER = "MB-3012"
    INCOMPLETE_CONTEXT = "MB-3013"


class AssertionRejectedError(Exception):
    """An assertion was not honoured. Carries a reason for the audit record."""

    def __init__(self, reason: RejectionReason, detail: str) -> None:
        super().__init__(f"{reason.value}: {detail}")
        self.reason = reason
        self.detail = detail


_REQUIRED_CONTEXT: Final = (
    "assertion_id",
    "key_id",
    "issuer",
    "grant_id",
    "case_id",
    "subject_token",
    "purpose",
    "actor_id",
    "actor_role",
)
"""§4.9: "There is no unscoped resolve." These fields are the scope."""


@dataclass(frozen=True, slots=True)
class GrantAssertion:
    """Zone 2's signed statement that a resolution is authorised.

    Carries no direct identifier. It names a token, a case, a purpose and an
    officer — never a person.
    """

    assertion_id: str
    key_id: str
    issuer: str
    issued_at: datetime
    expires_at: datetime
    operation: Operation
    grant_id: str
    grant_expires_at: datetime
    case_id: str
    subject_token: str
    purpose: str
    actor_id: str
    actor_role: str
    actor_unit_code: str
    actor_force_code: str
    second_approver_id: str | None = None


def sign_assertion(assertion: GrantAssertion, signing_key: Ed25519PrivateKey) -> str:
    """Serialise and sign an assertion. Called in Zone 2, never in Zone 3."""
    payload = _encode(_to_payload(assertion))
    body = f"{FORMAT_PREFIX}.{payload}"
    signature = signing_key.sign(body.encode())
    return f"{body}.{_b64(signature)}"


def verify_assertion(
    signed: str,
    *,
    expecting: Operation,
    trusted_keys: dict[str, Ed25519PublicKey],
    replay_guard: ReplayGuard,
    now: datetime | None = None,
) -> GrantAssertion:
    """Verify an assertion and consume it, or raise :class:`AssertionRejectedError`.

    Checks run in a deliberate order: authenticity first, then freshness, then
    terms. An assertion whose signature does not verify is never allowed to
    influence anything — including the replay guard, which is only consumed once
    the assertion is known to be genuine. Otherwise an attacker could burn the
    identifiers of legitimate assertions by replaying garbage.
    """
    now = now or datetime.now(UTC)
    assertion = _parse_and_authenticate(signed, trusted_keys)

    _check_freshness(assertion, now)
    _check_terms(assertion, expecting)

    if not replay_guard.consume(assertion.assertion_id, assertion.expires_at, now):
        raise AssertionRejectedError(
            RejectionReason.REPLAYED,
            f"Assertion {assertion.assertion_id} has already been spent.",
        )
    return assertion


def _parse_and_authenticate(
    signed: str, trusted_keys: dict[str, Ed25519PublicKey]
) -> GrantAssertion:
    parts = signed.split(".")
    if len(parts) != 3 or parts[0] != FORMAT_PREFIX or not all(parts[1:]):
        raise AssertionRejectedError(
            RejectionReason.MALFORMED,
            f"Expected three '{FORMAT_PREFIX}'-prefixed segments.",
        )
    _, payload_b64, signature_b64 = parts

    try:
        payload = json.loads(_unb64(payload_b64))
        signature = _unb64(signature_b64)
    except (ValueError, json.JSONDecodeError) as exc:
        raise AssertionRejectedError(
            RejectionReason.MALFORMED, f"Undecodable assertion: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise AssertionRejectedError(
            RejectionReason.MALFORMED, "Assertion payload is not an object."
        )

    key_id = payload.get("key_id")
    if not isinstance(key_id, str) or key_id not in trusted_keys:
        raise AssertionRejectedError(
            RejectionReason.UNKNOWN_KEY,
            f"Assertion names signing key {key_id!r}, which is not trusted here.",
        )

    try:
        trusted_keys[key_id].verify(
            signature, f"{FORMAT_PREFIX}.{payload_b64}".encode()
        )
    except InvalidSignature as exc:
        raise AssertionRejectedError(
            RejectionReason.BAD_SIGNATURE,
            f"Signature does not verify under key {key_id}.",
        ) from exc

    try:
        return _from_payload(payload)
    except (KeyError, TypeError, ValueError) as exc:
        raise AssertionRejectedError(
            RejectionReason.MALFORMED, f"Unusable assertion payload: {exc}"
        ) from exc


def _check_freshness(assertion: GrantAssertion, now: datetime) -> None:
    if assertion.issued_at - CLOCK_SKEW_TOLERANCE > now:
        raise AssertionRejectedError(
            RejectionReason.NOT_YET_VALID,
            f"Assertion is issued at {assertion.issued_at.isoformat()}, "
            f"beyond tolerated skew.",
        )
    if assertion.expires_at + CLOCK_SKEW_TOLERANCE <= now:
        raise AssertionRejectedError(
            RejectionReason.ASSERTION_EXPIRED,
            f"Assertion expired at {assertion.expires_at.isoformat()}.",
        )
    if assertion.expires_at - assertion.issued_at > MAX_ASSERTION_LIFETIME:
        raise AssertionRejectedError(
            RejectionReason.LIFETIME_TOO_LONG,
            f"Assertion lifetime exceeds {MAX_ASSERTION_LIFETIME}.",
        )
    if assertion.grant_expires_at <= now:
        raise AssertionRejectedError(
            RejectionReason.GRANT_EXPIRED,
            f"Grant {assertion.grant_id} expired at "
            f"{assertion.grant_expires_at.isoformat()}.",
        )


def _check_terms(assertion: GrantAssertion, expecting: Operation) -> None:
    if assertion.operation is not expecting:
        raise AssertionRejectedError(
            RejectionReason.OPERATION_MISMATCH,
            f"Assertion authorises {assertion.operation.value}, "
            f"but {expecting.value} was attempted.",
        )

    missing = [f for f in _REQUIRED_CONTEXT if not getattr(assertion, f)]
    if missing:
        raise AssertionRejectedError(
            RejectionReason.INCOMPLETE_CONTEXT,
            f"Assertion is missing required scope: {', '.join(missing)}.",
        )

    if expecting is Operation.BREAK_GLASS:
        if not assertion.second_approver_id:
            raise AssertionRejectedError(
                RejectionReason.SECOND_APPROVER_MISSING,
                "Break-glass requires second-person approval.",
            )
        if assertion.second_approver_id == assertion.actor_id:
            raise AssertionRejectedError(
                RejectionReason.SECOND_APPROVER_IS_ACTOR,
                f"Officer {assertion.actor_id} cannot approve their own "
                f"break-glass.",
            )
    elif assertion.second_approver_id:
        raise AssertionRejectedError(
            RejectionReason.UNEXPECTED_SECOND_APPROVER,
            "A routine resolve carries no second approver; the caller has "
            "confused the resolve and break-glass paths.",
        )


def _to_payload(assertion: GrantAssertion) -> dict[str, Any]:
    payload = asdict(assertion)
    payload["operation"] = assertion.operation.value
    for field in ("issued_at", "expires_at", "grant_expires_at"):
        payload[field] = getattr(assertion, field).astimezone(UTC).isoformat()
    return payload


def _from_payload(payload: dict[str, Any]) -> GrantAssertion:
    return GrantAssertion(
        assertion_id=payload["assertion_id"],
        key_id=payload["key_id"],
        issuer=payload["issuer"],
        issued_at=_timestamp(payload["issued_at"]),
        expires_at=_timestamp(payload["expires_at"]),
        operation=Operation(payload["operation"]),
        grant_id=payload["grant_id"],
        grant_expires_at=_timestamp(payload["grant_expires_at"]),
        case_id=payload["case_id"],
        subject_token=payload["subject_token"],
        purpose=payload["purpose"],
        actor_id=payload["actor_id"],
        actor_role=payload["actor_role"],
        actor_unit_code=payload["actor_unit_code"],
        actor_force_code=payload["actor_force_code"],
        second_approver_id=payload.get("second_approver_id"),
    )


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError(f"Timestamp {value!r} carries no timezone.")
    return parsed.astimezone(UTC)


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _encode(payload: dict[str, Any]) -> str:
    return _b64(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
