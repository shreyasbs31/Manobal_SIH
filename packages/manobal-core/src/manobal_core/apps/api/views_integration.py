"""Integration webhooks and feed health."""

from __future__ import annotations

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from manobal_core.apps.api.views import Unprocessable, _actor, _audit, _payload
from manobal_core.apps.authz.permissions import IsIntegration
from manobal_core.apps.governance.enums import AuditAction, LegalBasis, PurposeCode
from manobal_core.apps.governance.models import DataQualityReport, IngestBatch
from manobal_core.ingest.incidents import IncidentRefused, record_incident


class IntegrationIncidentsView(APIView):
    permission_classes = [IsIntegration]  # noqa: RUF012

    def post(self, request: Request) -> Response:
        principal = _actor(request)
        body = _payload(request)
        try:
            row = record_incident(
                unit_code=str(body.get("unit_code") or ""),
                occurred_at=str(body.get("occurred_at") or ""),
                category=str(body.get("category") or ""),
                source_system=str(body.get("source_system") or "ops"),
                external_id=str(body.get("external_id") or ""),
            )
        except IncidentRefused as exc:
            raise Unprocessable(f"MB-4220: {exc}") from exc
        _audit(
            principal,
            action=AuditAction.ADMIN_ACTION,
            purpose=PurposeCode.DATA_INGESTION,
            basis=LegalBasis.EMPLOYMENT,
            outcome="success",
            detail={"event": "incident.recorded", "unit": row.unit_id, "id": row.id},
        )
        return Response(
            {
                "id": row.id,
                "unit": row.unit_id,
                "occurred_at": row.occurred_at.isoformat(),
                "window_hours": row.window_hours,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class IntegrationHealthView(APIView):
    permission_classes = [IsIntegration]  # noqa: RUF012

    def get(self, request: Request) -> Response:
        principal = _actor(request)
        latest = IngestBatch.objects.order_by("-received_at").first()
        quality = DataQualityReport.objects.order_by("-period_end", "-id").first()
        _audit(
            principal,
            action=AuditAction.ADMIN_ACTION,
            purpose=PurposeCode.DATA_INGESTION,
            basis=LegalBasis.EMPLOYMENT,
            outcome="success",
            detail={"event": "integration.health"},
        )
        return Response(
            {
                "hrms": {
                    "last_received_at": (
                        latest.received_at.isoformat() if latest is not None else None
                    ),
                    "last_status": latest.status if latest is not None else None,
                    "accepted": latest.accepted_count if latest is not None else 0,
                    "quarantined": latest.quarantined_count if latest is not None else 0,
                },
                "quality": {
                    "source_system": quality.source_system if quality is not None else None,
                    "completeness": quality.completeness if quality is not None else None,
                    "period_end": (
                        quality.period_end.isoformat() if quality is not None else None
                    ),
                },
            }
        )
