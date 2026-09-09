"""Controlled vocabularies for the governance store.

Several of these exist to force a question into the data model rather than leave
it to a policy document. ``PurposeCode`` and ``LegalBasis`` are the clearest
case: SDD §7.3 requires that an access to individual-level data cannot be written
without a stated purpose, so both are non-null enumerated columns on every audit
row. An engineer adding a new read path has to answer "why are you looking at
this?" before the insert will succeed.
"""

from __future__ import annotations

from django.db import models


class Tier(models.TextChoices):
    """SDD §4.5. Stored as text so a database dump is readable in a review."""

    T0 = "T0", "Stable — within personal norm"
    T1 = "T1", "Watch — single-domain drift, visible only to the individual"
    T2 = "T2", "Elevated — two or more domains corroborating"
    T3 = "T3", "High — strong multi-domain deviation"
    T4 = "T4", "Acute — safety-critical indicator present"


#: The tiers at which an officer is told anything at all. T0 tells nobody and T1
#: tells only the individual, which is what makes the majority of the system's
#: output create no officer interaction (SDD §4.5).
OFFICER_VISIBLE_TIERS = frozenset({Tier.T2, Tier.T3, Tier.T4})

#: Narrower still for the medical officer, who §1.4 defines as an escalation
#: target rather than a reviewer of the routine queue. A T2 case is a welfare
#: conversation; sending it to a clinician medicalises ordinary distress and
#: widens the circle of people who know about it.
MEDICAL_OFFICER_TIERS = frozenset({Tier.T3, Tier.T4})


class DataType(models.TextChoices):
    """The consent granularity of FR-1.2 and §6.4.1.

    Each is independently grantable and independently withdrawable. They are not
    a hierarchy and there is no "accept all".
    """

    ORG = "org", "Duty, leave and deployment records the force already holds"
    SELF_REPORT = "selfreport", "Questionnaires and daily check-ins"
    BIOMETRIC = "biometric", "Heart rate, sleep and activity from a force-issued device"
    VOICE_FEATURES = "voice_features", "Voice measurements taken on your phone"
    TRANSCRIPT_EDGE = "transcript_edge", "Your words sent to the unit server (Tier B only)"
    JOURNAL = "journal", "Keeping a reflective entry"


class PurposeCode(models.TextChoices):
    """Why an actor touched a record. Mandatory on every audited access."""

    WELFARE_ASSESSMENT = "welfare_assessment", "Routine welfare scoring"
    CASE_REVIEW = "case_review", "Reviewing an assigned welfare case"
    ACUTE_RESPONSE = "acute_response", "Responding to a safety-critical signal"
    CLINICAL_REFERRAL = "clinical_referral", "Referral to a Medical Officer"
    SUBJECT_SELF_ACCESS = "subject_self_access", "The individual viewing their own data"
    CONSENT_MANAGEMENT = "consent_management", "Recording or withdrawing consent"
    ERASURE = "erasure", "Executing an erasure request"
    OVERSIGHT_AUDIT = "oversight_audit", "WDEC oversight"
    DATA_INGESTION = "data_ingestion", "Automated ingestion from a source system"
    GRIEVANCE = "grievance", "Investigating a contested flag or access"
    BREAK_GLASS = "break_glass", "Emergency override"


class LegalBasis(models.TextChoices):
    """The lawful ground for a processing action (SDD §7.9).

    ``VITAL_INTEREST`` is the sole basis on which the T4 path may override a
    refusal of contact, under DPDP Act 2023 §7(c)-(d) and the duty of care in
    MHCA 2017. It is a distinct value precisely so that every instance is
    countable, reviewable and reportable to the WDEC.
    """

    CONSENT = "consent", "DPDP Act 2023 §6 — consent"
    VITAL_INTEREST = "vital_interest", "DPDP Act 2023 §7(c)/(d) — vital interest"
    LEGAL_OBLIGATION = "legal_obligation", "Statutory duty"
    EMPLOYMENT = "employment", "DPDP Act 2023 §7(i) — employment purposes"
    SUBJECT_REQUEST = "subject_request", "Acting on the individual's own request"


class AuditAction(models.TextChoices):
    """SDD §7.3 lists what must be audited. This is that list, enumerated."""

    AUTH_SUCCESS = "auth.success", "Authentication succeeded"
    AUTH_FAILURE = "auth.failure", "Authentication failed"
    INDIVIDUAL_READ = "data.individual_read", "Individual-level data read"
    IDENTITY_RESOLVE = "identity.resolve", "Token resolved to a person"
    IDENTITY_TOKENISE = "identity.tokenise", "Service number tokenised"
    BREAK_GLASS = "identity.break_glass", "Break-glass override used"
    CONSENT_CHANGE = "consent.change", "Consent granted or withdrawn"
    ERASURE_REQUEST = "erasure.request", "Erasure requested"
    ERASURE_COMPLETE = "erasure.complete", "Erasure completed and receipt issued"
    DISCLOSURE_REQUEST = "disclosure.request", "Trend disclosure requested from subject"
    DISCLOSURE_RESPONSE = "disclosure.response", "Subject answered a disclosure request"
    OFFICER_DECISION = "case.decision", "Officer recorded a decision"
    ALERT_DISPATCH = "alert.dispatch", "Alert dispatched"
    RULESET_CHANGE = "ruleset.change", "Scoring ruleset changed"
    AGGREGATE_SUPPRESSED = "aggregate.suppressed", "Aggregate withheld below k"
    ADMIN_ACTION = "admin.action", "Administrative action"
    EXPORT = "data.export", "Data exported"
    ACCESS_DENIED = "authz.denied", "Access denied by predicate"


class Role(models.TextChoices):
    """SDD §6.2/§6.3 principals."""

    PERSONNEL = "personnel", "Personnel (data subject)"
    WELFARE_OFFICER = "welfare_officer", "Unit Welfare Officer"
    MEDICAL_OFFICER = "medical_officer", "Force Medical Officer"
    COMMANDER = "commander", "Commanding Officer"
    WDEC_AUDITOR = "wdec_auditor", "Welfare Data Ethics Cell auditor"
    INTEGRATION = "integration", "Source-system integration"


class CaseStatus(models.TextChoices):
    OPEN = "open", "Awaiting officer review"
    CONTACTED = "contacted", "Officer has made contact"
    RESOLVED = "resolved", "Closed with an outcome"
    #: FR-4.2 requires this to be a first-class, never-penalised outcome. An
    #: officer who closes a case as "no action needed" has used the system
    #: correctly, and the WDEC samples decision quality precisely so that
    #: closing cases this way is not treated as under-performance.
    NO_ACTION = "no_action", "Reviewed; no concern present"
    CONTESTED = "contested", "The individual has contested this flag"


class GrantScope(models.TextChoices):
    """What a time-boxed access grant actually permits (SDD §5.2 ACCESS_GRANT)."""

    FLAG = "flag", "Tier and contributing category names"
    CATEGORY_TREND = "category_trend", "The trend chart for one consented category"
    IDENTITY = "identity", "Resolution of the token to a person"
    CLINICAL_REFERRAL = "clinical_referral", "Clinical context for a Medical Officer"


class AlertChannel(models.TextChoices):
    IN_APP = "inapp", "In-app only"
    DIGEST = "digest", "Daily digest"
    PUSH = "push", "Push notification"
    SMS = "sms", "SMS via the NIC gateway"
    VOICE = "voice", "Telephonic escalation"


class DeliveryStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    SENT = "sent", "Sent"
    DELIVERED = "delivered", "Delivered"
    ACKNOWLEDGED = "acknowledged", "Acknowledged by the recipient"
    FAILED = "failed", "Failed"


class SubjectStatus(models.TextChoices):
    ACTIVE = "active", "Serving"
    TRANSFERRED = "transferred", "Transferred; previous officer access revoked"
    SEPARATED = "separated", "Separated from service"


class DeviceTier(models.TextChoices):
    """FR-1.8. The tier changes what leaves the phone, so it changes the consent
    text, so it is part of the consent record."""

    A = "A", "On-device model; no transcript leaves the phone"
    B = "B", "Edge-assisted; an ephemeral transcript reaches the unit server"


class ErasureStatus(models.TextChoices):
    """SDD §5.4. The saga's states are explicit because a withdrawal interrupted
    by a crash must be visibly incomplete and automatically retried, never
    silently half-done."""

    INTENT_RECORDED = "intent_recorded", "Erasure intent durably recorded"
    IN_PROGRESS = "in_progress", "Purging stores"
    COMPLETED = "completed", "All stores purged; receipt issued"
    FAILED = "failed", "Halted after retries; requires operator attention"
