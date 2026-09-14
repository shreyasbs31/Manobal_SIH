"""Per-store purge steps. Each function is idempotent.

Governance rows that are the system's memory of *itself* — the consent ledger,
the audit chain, published aggregates — are not purged here. Retracting those
would either destroy the proof of withdrawal or re-identify the person who left.
"""

from __future__ import annotations

from manobal_core.apps.biostore.models import PhysiologicalObservation
from manobal_core.apps.governance.enums import DataType
from manobal_core.apps.governance.models import AccessGrant, ErasureRequest
from manobal_core.apps.orgstore.models import (
    DutyObservation,
    EngagementObservation,
    LeaveObservation,
)
from manobal_core.apps.psystore.models import CheckinResponse, InstrumentResponse, JournalEntry
from manobal_core.apps.voicestore.models import VoiceObservation

ORG = "org_store"
PSY = "psy_store"
BIO = "bio_store"
VOICE = "voice_store"
OBJECTS = "object_store"

ALL_STORES: tuple[str, ...] = (ORG, PSY, BIO, VOICE, OBJECTS)

_TYPE_TO_STORES: dict[str, tuple[str, ...]] = {
    DataType.ORG: (ORG,),
    DataType.SELF_REPORT: (PSY,),
    DataType.JOURNAL: (PSY, OBJECTS),
    DataType.BIOMETRIC: (BIO,),
    DataType.VOICE_FEATURES: (VOICE,),
    DataType.TRANSCRIPT_EDGE: (VOICE,),
}


def stores_for(data_type: str | None) -> tuple[str, ...]:
    if not data_type:
        return ALL_STORES
    return _TYPE_TO_STORES.get(data_type, ())


def purge_org_store(request: ErasureRequest) -> None:
    token = request.subject_token
    DutyObservation.objects.filter(subject_token=token).delete()
    LeaveObservation.objects.filter(subject_token=token).delete()
    EngagementObservation.objects.filter(subject_token=token).delete()


def purge_psy_store(request: ErasureRequest) -> None:
    token = request.subject_token
    scope = request.data_type
    if scope in {None, DataType.SELF_REPORT}:
        InstrumentResponse.objects.filter(subject_token=token).delete()
        CheckinResponse.objects.filter(subject_token=token).delete()
    if scope in {None, DataType.JOURNAL}:
        JournalEntry.objects.filter(subject_token=token).delete()


def purge_bio_store(request: ErasureRequest) -> None:
    PhysiologicalObservation.objects.filter(subject_token=request.subject_token).delete()


def purge_voice_store(request: ErasureRequest) -> None:
    VoiceObservation.objects.filter(subject_token=request.subject_token).delete()


def purge_object_store(request: ErasureRequest) -> None:
    """Destroy journal keys. Ciphertext without a key is not readable.

    MinIO is still a no-op until an object store is wired. The key wipe is
    the part that must not wait on that work: a restored psy backup must not
    resurrect a withdrawn journal.
    """
    from manobal_core.apps.governance.enums import DataType
    from manobal_core.journal.crypto import destroy_keys

    if request.data_type in {None, "", DataType.JOURNAL}:
        destroy_keys(request.subject_token)
        _purge_object_sidecar(request.subject_token)


def _purge_object_sidecar(subject_token: str) -> None:
    """Tell a configured object store to drop journal blobs. Optional.

    MinIO is not in this process. When ``MANOBAL_OBJECT_PURGE_URL`` is an
    https endpoint the sidecar deletes ``journal/{token}`` objects. Without
    it, destroying the journal key is still enough: ciphertext cannot be read.
    """
    import json
    import os
    import urllib.error
    import urllib.request

    url = os.environ.get("MANOBAL_OBJECT_PURGE_URL", "").strip()
    if not url.startswith("https://"):
        return
    payload = json.dumps(
        {"subject_token": subject_token, "prefix": f"journal/{subject_token}"}
    ).encode()
    request = urllib.request.Request(  # noqa: S310
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    token = os.environ.get("MANOBAL_OBJECT_PURGE_TOKEN", "").strip()
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=5):  # noqa: S310
            return
    except (urllib.error.URLError, TimeoutError, OSError):
        return


def revoke_live_grants_for_subject(subject_token: str) -> int:
    """Close every live window onto this person (FR-7.5 transfer, FR-7.2 erasure)."""
    from django.utils import timezone

    return AccessGrant.objects.filter(
        subject_token=subject_token, revoked_at__isnull=True
    ).update(revoked_at=timezone.now())


def revoke_live_grants(request: ErasureRequest) -> None:
    """A full erasure ends every live window onto this person."""
    if request.data_type:
        return
    revoke_live_grants_for_subject(request.subject_token)


PURGERS: dict[str, object] = {
    ORG: purge_org_store,
    PSY: purge_psy_store,
    BIO: purge_bio_store,
    VOICE: purge_voice_store,
    OBJECTS: purge_object_store,
}
