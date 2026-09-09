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
    WdecBreakGlassView,
)
from .views_extra import (
    IngestCapturesView,
    MeAgentView,
    MeCheckinView,
    OfficerResolveView,
    RulesetApproveView,
    RulesetClinicalApproveView,
    RulesetProposeView,
)

urlpatterns = [
    path("v1/me/consent", ConsentView.as_view(), name="me-consent"),
    path("v1/me/assessment", MeAssessmentView.as_view(), name="me-assessment"),
    path("v1/me/sos", MeSosView.as_view(), name="me-sos"),
    path("v1/me/agent", MeAgentView.as_view(), name="me-agent"),
    path("v1/me/checkin", MeCheckinView.as_view(), name="me-checkin"),
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
    path("v1/commander/aggregates", CommanderAggregateView.as_view(), name="commander-aggregates"),
    path("v1/ingest/hrms", IngestHrmsView.as_view(), name="ingest-hrms"),
    path("v1/ingest/captures", IngestCapturesView.as_view(), name="ingest-captures"),
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
    path("v1/wdec/break-glass", WdecBreakGlassView.as_view(), name="wdec-break-glass"),
    path("v1/wdec/anchors", WdecAnchorsView.as_view(), name="wdec-anchors"),
]
