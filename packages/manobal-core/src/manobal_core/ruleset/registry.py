"""Dual-approval workflow for a signed ruleset artefact (§10.5)."""

from __future__ import annotations

from django.utils import timezone

from manobal_core.apps.governance.enums import AuditAction, LegalBasis, PurposeCode, Role
from manobal_core.apps.governance.models import AuditEvent, RulesetProposal, RulesetVersion


def register_proposal(
    *,
    version: str,
    digest: str,
    signature: str,
    signing_key_id: str,
    proposed_by: str,
    artefact_path: str = "",
    shadow_report: dict[str, object] | None = None,
) -> RulesetProposal:
    """Record a candidate. It is not active until both approvers sign."""
    return RulesetProposal.objects.create(
        version=version,
        digest=digest,
        signature=signature,
        signing_key_id=signing_key_id,
        artefact_path=artefact_path,
        shadow_report=shadow_report or {},
        proposed_by=proposed_by,
    )


def approve_proposal(
    proposal: RulesetProposal,
    *,
    actor_id: str,
    role: str,
) -> RulesetProposal:
    """Apply one of the two required signatures. Registers the version when both exist."""
    now = timezone.now()
    if role == Role.MEDICAL_OFFICER:
        if proposal.clinical_approver:
            raise ValueError("clinical approval is already recorded")
        proposal.clinical_approver = actor_id
        proposal.clinical_at = now
    elif role == Role.WDEC_AUDITOR:
        if proposal.wdec_approver:
            raise ValueError("wdec approval is already recorded")
        proposal.wdec_approver = actor_id
        proposal.wdec_at = now
    else:
        raise ValueError("only a medical officer or WDEC auditor may approve a ruleset")
    proposal.save(
        update_fields=["clinical_approver", "clinical_at", "wdec_approver", "wdec_at"]
    )
    if proposal.clinical_approver and proposal.wdec_approver:
        _register_version(proposal)
    AuditEvent.record(
        actor_id=actor_id,
        actor_role=role,
        action=AuditAction.RULESET_CHANGE,
        purpose_code=PurposeCode.OVERSIGHT_AUDIT,
        legal_basis=LegalBasis.LEGAL_OBLIGATION,
        outcome="success",
        detail={"proposal_id": proposal.id, "version": proposal.version},
    )
    return proposal


def _register_version(proposal: RulesetProposal) -> RulesetVersion:
    version = RulesetVersion.objects.create(
        version=proposal.version,
        digest=proposal.digest,
        signature=proposal.signature,
        signing_key_id=proposal.signing_key_id,
        approved_by_clinical=proposal.clinical_approver,
        approved_by_wdec=proposal.wdec_approver,
        approved_at=timezone.now(),
        shadow_report=proposal.shadow_report,
    )
    proposal.status = "registered"
    proposal.save(update_fields=["status"])
    return version
