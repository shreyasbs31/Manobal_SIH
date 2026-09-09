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
    """Journal ciphertext lives on the psy row. There is no separate object yet.

    The step still exists so a crash after psy and before MinIO would resume
    here once an object store is wired, rather than inventing a sixth status.
    """
    del request


def revoke_live_grants(request: ErasureRequest) -> None:
    """A full erasure ends every live window onto this person."""
    if request.data_type:
        return
    from django.utils import timezone

    AccessGrant.objects.filter(
        subject_token=request.subject_token, revoked_at__isnull=True
    ).update(revoked_at=timezone.now())


PURGERS: dict[str, object] = {
    ORG: purge_org_store,
    PSY: purge_psy_store,
    BIO: purge_bio_store,
    VOICE: purge_voice_store,
    OBJECTS: purge_object_store,
}
