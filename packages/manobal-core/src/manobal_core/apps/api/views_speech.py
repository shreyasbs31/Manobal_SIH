"""On-device recording is transcribed here. The vendor key never ships."""

from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from manobal_core.apps.api.views import Unprocessable, _actor, _audit
from manobal_core.apps.authz.permissions import IsPersonnel
from manobal_core.apps.authz.predicates import may_view_own_record
from manobal_core.apps.governance.enums import (
    AuditAction,
    DataType,
    LegalBasis,
    PurposeCode,
)
from manobal_core.apps.governance.models import ConsentEntry, Subject
from manobal_core.speech.deepgram import MAX_AUDIO_BYTES, deepgram_api_key, transcribe_audio


class MeTranscribeView(APIView):
    permission_classes = [IsPersonnel]  # noqa: RUF012
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # noqa: RUF012

    def post(self, request: Request) -> Response:
        principal = _actor(request)
        token = principal.subject_token
        if not may_view_own_record(principal, subject_token=token):
            raise PermissionDenied("MB-4030: you are not permitted to perform this action")
        subject = Subject.objects.filter(subject_token=token).first()
        if subject is None:
            raise Unprocessable("MB-4220: unknown subject")
        if not ConsentEntry.current_for(token).get(DataType.SELF_REPORT):
            raise Unprocessable("MB-4220: self-report consent is required")
        if not deepgram_api_key():
            return Response(
                {
                    "type": "https://manobal.gov.in/problems/mb-5030",
                    "title": "Transcription is not configured.",
                    "status": 503,
                    "code": "MB-5030",
                    "detail": "Transcription is not configured.",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        upload = request.FILES.get("audio")
        if upload is None:
            raise Unprocessable("MB-4220: audio is required")
        payload = upload.read()
        if not payload or len(payload) > MAX_AUDIO_BYTES:
            raise Unprocessable("MB-4220: audio is missing or too large")
        language = str(request.data.get("language") or "en")
        transcript = transcribe_audio(
            payload,
            content_type=str(getattr(upload, "content_type", "") or "audio/m4a"),
            language=language,
        )
        _audit(
            principal,
            action=AuditAction.INDIVIDUAL_READ,
            purpose=PurposeCode.SUBJECT_SELF_ACCESS,
            basis=LegalBasis.CONSENT,
            outcome="success",
            subject_token=token,
            detail={"event": "speech.transcribed", "chars": len(transcript)},
        )
        return Response({"transcript": transcript})
