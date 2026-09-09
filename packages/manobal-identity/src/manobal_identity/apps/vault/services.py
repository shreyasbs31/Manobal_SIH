"""The two directions across the identity boundary (SDD §4.9, §4.4).

§4.4 is explicit that "tokenisation direction matters. The ingest worker may ask
'what is the token for this service number?' It may **not** ask the reverse."
That asymmetry is the reason this module has two entry points rather than one
function with a mode flag: :meth:`IdentityVault.tokenise` cannot return an
identity because it has no code path that decrypts anything, and
:meth:`IdentityVault.resolve` cannot be reached without a signed grant.

A flag would have made the difference a runtime condition. Two functions make it
a structural one, which is the standard §3.2 sets: components are not trusted to
decline, they are made unable.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from django.db import transaction

from manobal_identity.apps.vault.models import (
    Direction,
    ResolutionAudit,
    SubjectIdentity,
)
from manobal_identity.crypto.blind_index import blind_index
from manobal_identity.crypto.envelope import EnvelopeCipher, SealedValue, field_aad
from manobal_identity.crypto.kms import KeyManagementService
from manobal_identity.crypto.tokens import mint_subject_token
from manobal_identity.grants.assertion import (
    AssertionRejectedError,
    GrantAssertion,
    Operation,
    verify_assertion,
)
from manobal_identity.grants.replay import ReplayGuard
from manobal_identity.policy.resolution import (
    Anomaly,
    PolicyOutcome,
    ResolutionCounts,
    evaluate_resolution,
)

logger = logging.getLogger(__name__)

_ENCRYPTED_FIELDS: Final = ("service_no", "full_name", "rank_code", "mobile_e164")


class ResolutionDeniedError(Exception):
    """The resolution was refused. Always audited before it is raised."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


class SubjectNotFoundError(Exception):
    """No vault row for that token."""


@dataclass(frozen=True, slots=True)
class PersonRecord:
    """An identity as supplied by HRMS at the ingest boundary."""

    service_no: str
    full_name: str
    rank_code: str
    mobile_e164: str
    unit_code: str
    unit_path: str
    force_code: str
    enrolled_on: datetime


@dataclass(frozen=True, slots=True)
class ResolvedIdentity:
    """The answer to an authorised resolution. Never logged, never cached."""

    subject_token: str
    service_no: str
    full_name: str
    rank_code: str
    mobile_e164: str
    unit_code: str
    force_code: str

    def __repr__(self) -> str:
        return f"ResolvedIdentity(subject_token={self.subject_token!r}, ...=<redacted>)"


@dataclass(frozen=True, slots=True)
class CallerContext:
    """Who is calling, as established by mTLS and the workload allow-list."""

    workload_id: str
    source_ip: str | None = None


class IdentityVault:
    """The only object in the system that can connect a token to a person."""

    def __init__(
        self,
        kms: KeyManagementService,
        replay_guard: ReplayGuard,
        trusted_keys: dict[str, Ed25519PublicKey],
    ) -> None:
        self._kms = kms
        self._cipher = EnvelopeCipher(kms)
        self._replay_guard = replay_guard
        self._trusted_keys = trusted_keys

    # ---------------------------------------------------------------- write

    def tokenise(
        self, people: Sequence[PersonRecord], caller: CallerContext
    ) -> dict[str, str]:
        """Map service numbers to tokens, enrolling anyone not yet known.

        Returns ``{service_no: subject_token}`` and nothing else. There is no
        branch in this method that decrypts a field, so no caller — however
        privileged, however compromised — can turn it into a lookup.

        Enrolment is idempotent. The nightly HRMS delta re-sends people who are
        already enrolled, and a second token for an existing person would split
        their history in two and destroy both halves' baselines.
        """
        tokens: dict[str, str] = {}
        created = 0

        with transaction.atomic():
            for person in people:
                index = blind_index(person.service_no, self._kms)
                existing = (
                    SubjectIdentity.objects.filter(service_no_index=index)
                    .values_list("subject_token", flat=True)
                    .first()
                )
                if existing:
                    tokens[person.service_no] = existing
                    continue
                tokens[person.service_no] = self._enrol(person, index)
                created += 1

            ResolutionAudit.record(
                direction=Direction.TOKENISE,
                granted=True,
                actor_id=caller.workload_id,
                actor_role="workload",
                workload_id=caller.workload_id,
                purpose_code="ingest_boundary_tokenisation",
                record_count=len(people),
                source_ip=caller.source_ip,
            )

        logger.info(
            "tokenised batch",
            extra={"requested": len(people), "enrolled": created},
        )
        return tokens

    def _enrol(self, person: PersonRecord, index: str) -> str:
        token = mint_subject_token()
        key = self._cipher.new_record_key()

        sealed = {
            f"{field}_enc": bytes(
                self._cipher.seal(
                    key, getattr(person, field), aad=field_aad(field, token)
                )
            )
            for field in _ENCRYPTED_FIELDS
        }

        SubjectIdentity.objects.create(
            subject_token=token,
            service_no_index=index,
            wrapped_key=key.wrapped,
            key_version=key.kek_version,
            current_unit_code=person.unit_code,
            current_unit_path=person.unit_path,
            force_code=person.force_code,
            enrolled_on=person.enrolled_on,
            **sealed,
        )
        return token

    # ----------------------------------------------------------------- read

    def resolve(
        self,
        signed_assertion: str,
        *,
        operation: Operation,
        caller: CallerContext,
        now: datetime | None = None,
    ) -> ResolvedIdentity:
        """Turn a token into a person, if everything permits it.

        The order of operations is load-bearing:

        1.  verify the grant assertion — an unauthenticated caller learns
            nothing, not even whether the token exists;
        2.  load the row's *metadata* — unit and force, which are not
            identifying and which the policy needs;
        3.  apply the rate limits and anomaly checks;
        4.  **write the audit entry**, then
        5.  decrypt.

        Step 4 precedes step 5 because of §5.4: audited before the read, so a
        crash between them leaves a record of a resolution that did not quite
        happen rather than a resolution nobody can see.
        """
        now = now or datetime.now(UTC)
        assertion = verify_assertion(
            signed_assertion,
            expecting=operation,
            trusted_keys=self._trusted_keys,
            replay_guard=self._replay_guard,
            now=now,
        )

        try:
            row = SubjectIdentity.objects.get(subject_token=assertion.subject_token)
        except SubjectIdentity.DoesNotExist as exc:
            self._audit(assertion, operation, caller, granted=False,
                        denial="MB-3404", anomalies=())
            raise SubjectNotFoundError(
                f"No vault entry for {assertion.subject_token}."
            ) from exc

        outcome = evaluate_resolution(
            operation=operation,
            counts=self._counts_for(assertion.actor_id, now),
            actor_unit_code=assertion.actor_unit_code,
            subject_unit_path=row.current_unit_path,
        )

        self._audit(
            assertion,
            operation,
            caller,
            granted=outcome.allowed,
            denial=outcome.denial.value if outcome.denial else "",
            anomalies=outcome.anomalies,
        )

        if outcome.notify_wdec:
            self._notify_wdec(assertion, outcome)

        if not outcome.allowed:
            assert outcome.denial is not None
            raise ResolutionDeniedError(
                outcome.denial.value,
                f"Resolution refused for actor {assertion.actor_id}.",
            )

        return self._decrypt(row)

    def _decrypt(self, row: SubjectIdentity) -> ResolvedIdentity:
        key = self._cipher.load_record_key(bytes(row.wrapped_key))
        plain = {
            field: self._cipher.open(
                key,
                SealedValue.from_bytes(bytes(getattr(row, f"{field}_enc"))),
                aad=field_aad(field, row.subject_token),
            )
            for field in _ENCRYPTED_FIELDS
        }
        return ResolvedIdentity(
            subject_token=row.subject_token,
            unit_code=row.current_unit_code,
            force_code=row.force_code,
            **plain,
        )

    def _counts_for(self, actor_id: str, now: datetime) -> ResolutionCounts:
        """Count what this officer has already been *granted*.

        Refused attempts are excluded: they disclosed nothing, and counting
        them would let a caller exhaust an officer's quota by making requests
        that were never going to succeed.
        """
        granted = ResolutionAudit.objects.filter(actor_id=actor_id, granted=True)
        return ResolutionCounts(
            resolves_last_hour=granted.filter(
                direction=Direction.RESOLVE, occurred_at__gte=now - timedelta(hours=1)
            ).count(),
            resolves_last_day=granted.filter(
                direction=Direction.RESOLVE, occurred_at__gte=now - timedelta(days=1)
            ).count(),
            break_glass_last_day=granted.filter(
                direction=Direction.BREAK_GLASS,
                occurred_at__gte=now - timedelta(days=1),
            ).count(),
        )

    def _audit(
        self,
        assertion: GrantAssertion,
        operation: Operation,
        caller: CallerContext,
        *,
        granted: bool,
        denial: str,
        anomalies: tuple[Anomaly, ...],
    ) -> None:
        ResolutionAudit.record(
            direction=(
                Direction.BREAK_GLASS
                if operation is Operation.BREAK_GLASS
                else Direction.RESOLVE
            ),
            granted=granted,
            denial_reason=denial,
            actor_id=assertion.actor_id,
            actor_role=assertion.actor_role,
            actor_unit_code=assertion.actor_unit_code,
            workload_id=caller.workload_id,
            subject_token=assertion.subject_token,
            case_id=assertion.case_id,
            grant_id=assertion.grant_id,
            assertion_id=assertion.assertion_id,
            purpose_code=assertion.purpose,
            anomalies=[a.value for a in anomalies],
            source_ip=caller.source_ip,
        )

    def _notify_wdec(self, assertion: GrantAssertion, outcome: PolicyOutcome) -> None:
        """Raise the anomaly for the WDEC (§4.9: within 60 seconds).

        Emitted as a log event at WARNING; the alerting pipeline in §8.3 routes
        on it. It deliberately names the officer and the case but not the
        subject's identity — the WDEC needs to know that a boundary was crossed
        and by whom, not who was on the other side of it.
        """
        logger.warning(
            "identity resolution anomaly",
            extra={
                "event": "wdec.identity_anomaly",
                "anomalies": [a.value for a in outcome.anomalies],
                "actor_id": assertion.actor_id,
                "actor_unit_code": assertion.actor_unit_code,
                "case_id": assertion.case_id,
                "allowed": outcome.allowed,
                "flag_session": outcome.flag_session,
            },
        )


__all__ = [
    "AssertionRejectedError",
    "CallerContext",
    "IdentityVault",
    "PersonRecord",
    "ResolutionDeniedError",
    "ResolvedIdentity",
    "SubjectNotFoundError",
]
