"""HTTP routes for the analytics plane."""

from __future__ import annotations

from django.urls import path

from .views import (
    CommanderAggregateView,
    ConsentView,
    IngestHrmsView,
    MeAssessmentView,
    MeSosView,
    OfficerCaseView,
    OfficerContactView,
    OfficerDecisionView,
    OfficerQueueView,
    WdecAnchorsView,
    WdecBreakGlassReviewView,
    WdecBreakGlassView,
)
from .views_casework import (
    ClinicalQueueView,
    OfficerClinicalReferView,
    OfficerDisclosureView,
    OfficerTrendView,
)
from .views_destinations import OfficerDestinationView
from .views_enrolment import MeDeviceRevokeView, MeDevicesView
from .views_extra import (
    IngestCapturesView,
    MeAgentView,
    MeCheckinView,
    OfficerResolveView,
    RulesetApproveView,
    RulesetClinicalApproveView,
    RulesetProposeView,
)
from .views_integration import IntegrationHealthView, IntegrationIncidentsView
from .views_oversight import IngestSeparationsView, WdecAuditView, WdecFairnessView
from .views_personnel import (
    MeCasesView,
    MeContestView,
    MeDisclosureAnswerView,
    MeDisclosureListView,
    MeInstrumentCatalogueView,
    MeInstrumentSubmitView,
    MeJournalView,
)
from .views_rights import (
    MeConsentLedgerView,
    MeErasureDetailView,
    MeErasureView,
    MeHelplineView,
    MeInsightsView,
    MeJournalEntryView,
    MeTrendsView,
)
from .views_speech import MeTranscribeView

urlpatterns = [
    path("v1/me/consent", ConsentView.as_view(), name="me-consent"),
    path("v1/me/consent/ledger", MeConsentLedgerView.as_view(), name="me-consent-ledger"),
    path("v1/me/assessment", MeAssessmentView.as_view(), name="me-assessment"),
    path("v1/me/trends", MeTrendsView.as_view(), name="me-trends"),
    path("v1/me/insights", MeInsightsView.as_view(), name="me-insights"),
    path("v1/me/helpline", MeHelplineView.as_view(), name="me-helpline"),
    path("v1/me/erasure", MeErasureView.as_view(), name="me-erasure"),
    path("v1/me/erasure/<int:request_id>", MeErasureDetailView.as_view(), name="me-erasure-detail"),
    path("v1/me/sos", MeSosView.as_view(), name="me-sos"),
    path("v1/me/agent", MeAgentView.as_view(), name="me-agent"),
    path("v1/me/transcribe", MeTranscribeView.as_view(), name="me-transcribe"),
    path("v1/me/checkin", MeCheckinView.as_view(), name="me-checkin"),
    path("v1/me/journal", MeJournalView.as_view(), name="me-journal"),
    path("v1/me/journal/<int:entry_id>", MeJournalEntryView.as_view(), name="me-journal-entry"),
    path("v1/me/instruments", MeInstrumentSubmitView.as_view(), name="me-instruments"),
    path(
        "v1/me/instruments/catalogue",
        MeInstrumentCatalogueView.as_view(),
        name="me-instrument-catalogue",
    ),
    path("v1/me/cases", MeCasesView.as_view(), name="me-cases"),
    path("v1/me/cases/<int:case_id>/contest", MeContestView.as_view(), name="me-contest"),
    path("v1/me/disclosures", MeDisclosureListView.as_view(), name="me-disclosures"),
    path(
        "v1/me/disclosures/<int:request_id>",
        MeDisclosureAnswerView.as_view(),
        name="me-disclosure-answer",
    ),
    path("v1/me/devices", MeDevicesView.as_view(), name="me-devices"),
    path(
        "v1/me/devices/<int:device_id>/revoke",
        MeDeviceRevokeView.as_view(),
        name="me-device-revoke",
    ),
    path("v1/officer/destination", OfficerDestinationView.as_view(), name="officer-destination"),
    path("v1/officer/queue", OfficerQueueView.as_view(), name="officer-queue"),
    path("v1/officer/cases/<int:case_id>", OfficerCaseView.as_view(), name="officer-case"),
    path(
        "v1/officer/cases/<int:case_id>/contact",
        OfficerContactView.as_view(),
        name="officer-case-contact",
    ),
    path(
        "v1/officer/cases/<int:case_id>/decision",
        OfficerDecisionView.as_view(),
        name="officer-case-decision",
    ),
    path(
        "v1/officer/cases/<int:case_id>/resolve",
        OfficerResolveView.as_view(),
        name="officer-case-resolve",
    ),
    path(
        "v1/officer/cases/<int:case_id>/disclosure",
        OfficerDisclosureView.as_view(),
        name="officer-case-disclosure",
    ),
    path(
        "v1/officer/cases/<int:case_id>/trend",
        OfficerTrendView.as_view(),
        name="officer-case-trend",
    ),
    path(
        "v1/officer/cases/<int:case_id>/refer-clinical",
        OfficerClinicalReferView.as_view(),
        name="officer-case-refer-clinical",
    ),
    path("v1/clinical/queue", ClinicalQueueView.as_view(), name="clinical-queue"),
    path("v1/commander/aggregates", CommanderAggregateView.as_view(), name="commander-aggregates"),
    path("v1/ingest/hrms", IngestHrmsView.as_view(), name="ingest-hrms"),
    path("v1/ingest/captures", IngestCapturesView.as_view(), name="ingest-captures"),
    path("v1/captures:batch", IngestCapturesView.as_view(), name="captures-batch"),
    path("v1/ingest/separations", IngestSeparationsView.as_view(), name="ingest-separations"),
    path("v1/wdec/rulesets", RulesetProposeView.as_view(), name="wdec-ruleset-propose"),
    path(
        "v1/wdec/rulesets/<int:proposal_id>/approve",
        RulesetApproveView.as_view(),
        name="wdec-ruleset-approve",
    ),
    path(
        "v1/clinical/rulesets/<int:proposal_id>/approve",
        RulesetClinicalApproveView.as_view(),
        name="clinical-ruleset-approve",
    ),
    path(
        "v1/integration/incidents",
        IntegrationIncidentsView.as_view(),
        name="integration-incidents",
    ),
    path("v1/integration/health", IntegrationHealthView.as_view(), name="integration-health"),
    path("v1/wdec/break-glass", WdecBreakGlassView.as_view(), name="wdec-break-glass"),
    path(
        "v1/wdec/break-glass/<int:grant_id>/review",
        WdecBreakGlassReviewView.as_view(),
        name="wdec-break-glass-review",
    ),
    path("v1/wdec/anchors", WdecAnchorsView.as_view(), name="wdec-anchors"),
    path("v1/wdec/fairness", WdecFairnessView.as_view(), name="wdec-fairness"),
    path("v1/wdec/audit", WdecAuditView.as_view(), name="wdec-audit"),
]
