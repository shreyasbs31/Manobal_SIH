from __future__ import annotations

import copy
import json
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import yaml

from .audit import chain_hash, verify_chain_entries
from .config import get_settings, live_providers_enabled
from .errors import ApiError
from .observability import (
    cost_guard_active,
    metrics_payload,
    reset_metrics,
    set_cost_guard,
)
from .privacy.rights import KILLSWITCHES, set_killswitch
from .providers.router import PROVIDER_CALLS, get_router
from .scoring.overlays import compute_overlays
from .scoring.forecast import EXCLUDED_ATTRIBUTES, REGISTRY, metrics, register_world_metrics, train_forecast
from .scoring.ruleset import load_ruleset, verify_yaml

GENESIS = "0" * 64

SHOTS: list[dict[str, str]] = [
    {
        "id": "landing",
        "label": "Landing ribbon",
        "persona": "public",
        "phone": "/app",
        "console": "/command",
        "href": "/",
        "clicks": "Open / then wait for the ribbon to draw.",
    },
    {
        "id": "onboarding",
        "label": "Hindi onboarding",
        "persona": "arjun",
        "phone": "/app/onboarding",
        "console": "/welfare",
        "href": "/stage?phone=/app/onboarding&console=/welfare&shot=onboarding",
        "clicks": "Sign in as Arjun. Language Hindi. Accept the one exception. Finish receipt.",
    },
    {
        "id": "checkin",
        "label": "Twenty second check-in",
        "persona": "arjun",
        "phone": "/app/check-in",
        "console": "/welfare",
        "href": "/stage?phone=/app/check-in&console=/welfare&shot=checkin",
        "clicks": "Face scale, two tags, save. Wait for the ribbon join.",
    },
    {
        "id": "voice",
        "label": "Hindi voice check-in",
        "persona": "arjun",
        "phone": "/app/saathi",
        "console": "/welfare",
        "href": "/stage?phone=/app/saathi&console=/welfare&shot=voice&fixture=arjun-hi",
        "clicks": "Sign in as Arjun. Open Saathi. Click Play recorded check-in. Hindi captions and audio-cleared should appear.",
        "expect": "Saathi replies in Hindi. Audio-cleared chip after the turn. No safety screen.",
    },
    {
        "id": "drift",
        "label": "Arjun time travel",
        "persona": "arjun",
        "phone": "/app",
        "console": "/welfare",
        "href": "/stage?phone=/app&console=/welfare&shot=drift",
        "clicks": "Director +1 week, run nightly, then open Arjun home.",
    },
    {
        "id": "workspace",
        "label": "Case workspace reveal",
        "persona": "arjun",
        "phone": "/app/me",
        "console": "/welfare/cases/MB-4091",
        "href": "/stage?phone=/app/me&console=/welfare/cases/MB-4091&shot=workspace",
        "clicks": "Purpose care contact. Justify. Reveal. Watch the ledger on the phone.",
    },
    {
        "id": "imran-thomas",
        "label": "Imran and Thomas stay steady",
        "persona": "imran",
        "phone": "/app",
        "console": "/lab",
        "href": "/stage?phone=/app&console=/lab&shot=imran-thomas",
        "clicks": "Lab copy: Imran stays T1, Thomas stays T0.",
    },
    {
        "id": "formation",
        "label": "Formation and hidden tile",
        "persona": "commander",
        "phone": "/app",
        "console": "/command",
        "href": "/stage?phone=/app&console=/command&shot=formation",
        "clicks": "Point at Post D-7. It stays hatched. No names.",
    },
    {
        "id": "copilot",
        "label": "Copilot Hindi refusal",
        "persona": "commander",
        "phone": "/app",
        "console": "/command",
        "href": "/stage?phone=/app&console=/command&shot=copilot",
        "clicks": "Open copilot. Ask: Charlie Coy mein kaun pareshan hai?",
        "expect": "Refusal in Hindi. No name. Unit share 20 to 30 percent. Chart still shows.",
    },
    {
        "id": "copilot-aggregate",
        "label": "Copilot Hindi aggregate",
        "persona": "commander",
        "phone": "/app",
        "console": "/command",
        "href": "/stage?phone=/app&console=/command&shot=copilot-aggregate",
        "clicks": "Open copilot. Click the Hindi duty-hours question. Press Ask.",
        "expect": "Live main model answers in Hindi about the unit. A chart appears. No names.",
    },
    {
        "id": "roster",
        "label": "Roster balancer",
        "persona": "commander",
        "phone": "/app",
        "console": "/command/roster",
        "href": "/stage?phone=/app&console=/command/roster&shot=roster",
        "clicks": "Move a slider. Small groups stay locked.",
    },
    {
        "id": "deepak",
        "label": "Deepak safety and T4",
        "persona": "deepak",
        "phone": "/app/saathi",
        "console": "/welfare",
        "href": "/stage?phone=/app/saathi&console=/welfare&shot=deepak&fixture=deepak-distress",
        "clicks": "Sign in as Deepak. Type 'main jeena nahi chahta', then Play recorded check-in for the spoken path.",
        "expect": "No model reply. Safety screen. T4 on Welfare and Medical within 5 seconds.",
    },
    {
        "id": "deepak-typed",
        "label": "Deepak typed distress",
        "persona": "deepak",
        "phone": "/app/saathi",
        "console": "/welfare",
        "href": "/stage?phone=/app/saathi&console=/welfare&shot=deepak-typed",
        "clicks": "Sign in as Deepak. Keyboard. Type main jeena nahi chahta. Send.",
        "expect": "No model reply. Safety screen. Welfare and Medical show T4.",
    },
    {
        "id": "governance",
        "label": "Governance chain",
        "persona": "wdec",
        "phone": "/app",
        "console": "/governance",
        "href": "/stage?phone=/app&console=/governance&shot=governance",
        "clicks": "Verify, tamper, restore. Acute kill stays locked.",
    },
    {
        "id": "lab",
        "label": "Validation lab",
        "persona": "wdec",
        "phone": "/app",
        "console": "/lab",
        "href": "/stage?phone=/app&console=/lab&shot=lab",
        "clicks": "Toggle shifted world. Read the source line under the figures.",
        "expect": "Precision, recall, and Brier come from core or demo cases. Source line is visible. Imran T1, Thomas T0.",
    },
    {
        "id": "offline",
        "label": "Offline then sync",
        "persona": "arjun",
        "phone": "/app/check-in",
        "console": "/architecture",
        "href": "/stage?phone=/app/check-in&console=/architecture&shot=offline",
        "clicks": "Airplane on, check-in, toolkit, SMS. Airplane off, drain queue.",
    },
    {
        "id": "architecture",
        "label": "Zones and self-test",
        "persona": "public",
        "phone": "/app",
        "console": "/architecture",
        "href": "/stage?phone=/app&console=/architecture&shot=architecture",
        "clicks": "Packets, Zone X hatch, vault isolation, mode panel.",
    },
    {
        "id": "close",
        "label": "Landing second fold",
        "persona": "public",
        "phone": "/app",
        "console": "/command",
        "href": "/#ps-map",
        "clicks": "Scroll to the expected-solution mapping table.",
    },
    {
        "id": "karthik",
        "label": "Karthik Tamil voice",
        "persona": "karthik",
        "phone": "/app/saathi",
        "console": "/welfare",
        "href": "/stage?phone=/app/saathi&console=/welfare&shot=karthik&fixture=karthik-ta",
        "clicks": "Sign in as Karthik. Click Play recorded check-in.",
        "expect": "Tamil captions. Saathi replies. Audio-cleared chip. No safety screen.",
    },
    {
        "id": "rajesh",
        "label": "Rajesh grievance lever",
        "persona": "rajesh",
        "phone": "/app",
        "console": "/welfare/cases/MB-4091",
        "href": "/stage?phone=/app&console=/welfare&shot=rajesh",
        "clicks": "Open Rajesh if listed, else Welfare High tab.",
    },
    {
        "id": "lalit",
        "label": "Lalit incident protocol",
        "persona": "lalit",
        "phone": "/app/talk",
        "console": "/welfare",
        "href": "/stage?phone=/app/talk&console=/welfare&shot=lalit",
        "clicks": "Incident card on Welfare. No names on Command.",
    },
    {
        "id": "meena",
        "label": "Meena leave planner",
        "persona": "meena",
        "phone": "/app/rest",
        "console": "/command/roster",
        "href": "/stage?phone=/app/rest&console=/command/roster&shot=meena",
        "clicks": "EL/CL window. Copy says MANOBAL does not submit leave.",
    },
    {
        "id": "hindi-brief",
        "label": "Hindi case brief",
        "persona": "uwo",
        "phone": "/app/me",
        "console": "/welfare/cases/MB-4091",
        "href": "/stage?phone=/app/me&console=/welfare/cases/MB-4091&shot=hindi-brief",
        "clicks": "Sign in as welfare. Open MB-4091. Brief language Hindi.",
        "expect": "Four sentences with [tier] [domain] [onset] [lever] field marks.",
    },
    {
        "id": "deepgram-outage",
        "label": "Deepgram outage fallback",
        "persona": "meena",
        "phone": "/app/saathi",
        "console": "/governance",
        "href": "/stage?phone=/app/saathi&console=/governance&shot=deepgram-outage&fixture=meena-en",
        "clicks": "Director: Simulate outage with provider deepgram. Sign in as Meena. Play recorded check-in.",
        "expect": "Turn still completes via Azure Speech. Captions appear.",
    },
]

SCENARIOS: dict[str, dict[str, str]] = {
    "arjun_drift": {
        "label": "Arjun drift",
        "phone": "/app",
        "console": "/welfare",
        "shot": "drift",
    },
    "deepak_acute": {
        "label": "Deepak acute",
        "phone": "/app/safety",
        "console": "/medical",
        "shot": "deepak",
    },
    "lalit_incident": {
        "label": "Lalit incident",
        "phone": "/app/talk",
        "console": "/welfare",
        "shot": "lalit",
    },
    "meena_leave": {
        "label": "Meena leave",
        "phone": "/app/rest",
        "console": "/command/roster",
        "shot": "meena",
    },
    "karthik_return": {
        "label": "Karthik return",
        "phone": "/app",
        "console": "/welfare",
        "shot": "karthik",
    },
    "rajesh_grievance": {
        "label": "Rajesh grievance",
        "phone": "/app",
        "console": "/welfare",
        "shot": "rajesh",
    },
    "imran_stable": {
        "label": "Imran stable",
        "phone": "/app",
        "console": "/lab",
        "shot": "imran-thomas",
    },
    "thomas_baseline": {
        "label": "Thomas baseline",
        "phone": "/app",
        "console": "/lab",
        "shot": "imran-thomas",
    },
    "outage": {
        "label": "Provider outage",
        "phone": "/app/saathi",
        "console": "/governance",
        "shot": "governance",
    },
    "offline_sync": {
        "label": "Offline then sync",
        "phone": "/app/check-in",
        "console": "/architecture",
        "shot": "offline",
    },
    "governance_tamper": {
        "label": "Chain tamper",
        "phone": "/app",
        "console": "/governance",
        "shot": "governance",
    },
    "lab_shifted": {
        "label": "Shifted world",
        "phone": "/app",
        "console": "/lab",
        "shot": "lab",
    },
}

_chain: list[dict[str, str | int]] = []
_chain_mode = "intact"
_dpo_requests: list[dict[str, Any]] = []
_dpo_breaches: list[dict[str, str]] = []
_dpo_notices: list[dict[str, str]] = []
_jobs: list[dict[str, Any]] = []
_quarantine: list[dict[str, str]] = []
_schedules: list[dict[str, Any]] = []
_assignments: list[dict[str, str]] = []
_flags: dict[str, bool] = {"simple_mode_default": False, "machine_translate": True}
_corpus_state: dict[str, Any] = {
    "reviewed_en": 32,
    "reviewed_hi": 32,
    "pending": 0,
    "embedded_at": "2026-09-16 02:00 IST",
}
_clock = {
    "sim_now": "2026-09-16T10:00:00+05:30",
    "running": True,
    "speed": 1.0,
}
_scenario = "arjun_drift"
_transparency: dict[str, Any] | None = None
_reviews: list[dict[str, str]] = [
    {
        "id": "rev-01",
        "kind": "identity reveal",
        "status": "open",
        "note": "Purpose was care contact. Contact note is due.",
    }
]


def _build_chain() -> list[dict[str, str | int]]:
    prev = GENESIS
    rows: list[dict[str, str | int]] = []
    for seq, canonical in enumerate(
        ("genesis", "anchor.daily", "ruleset.v1", "score.window", "grant.note"),
        start=1,
    ):
        digest = chain_hash(prev, canonical)
        rows.append({"seq": seq, "prev_hash": prev, "hash": digest, "canonical": canonical})
        prev = digest
    return rows


def _ensure_chain() -> None:
    global _chain
    if not _chain:
        _chain = _build_chain()


def ensure_lab_worlds() -> None:
    if "primary" in REGISTRY and "shifted" in REGISTRY:
        return
    import numpy as np

    rng = np.random.default_rng(4)
    features = rng.normal(size=(48, 4))
    labels = (features[:, 0] + features[:, 1] > 0).astype(int)
    names = ["workload_z", "body_vitals_z", "cusum_max", "coverage"]
    model = train_forecast(features, labels, names)
    probs = model.calibrator.predict(model.booster.predict(features))
    register_world_metrics("primary", metrics(labels, probs), version=model.version)
    shifted = (features[:, 0] * 1.15 + features[:, 1] > 0.05).astype(int)
    register_world_metrics("shifted", metrics(shifted, probs), version=model.version)


def _seed_dpo() -> None:
    if _dpo_requests:
        return
    due = (datetime.now(UTC) + timedelta(days=7)).date().isoformat()
    _dpo_requests.extend(
        [
            {
                "id": "dpo-access-01",
                "kind": "access",
                "status": "open",
                "due": due,
                "token_hint": "st_****19",
            },
            {
                "id": "dpo-erase-01",
                "kind": "erasure",
                "status": "open",
                "due": due,
                "token_hint": "st_****04",
            },
            {
                "id": "dpo-griev-01",
                "kind": "grievance",
                "status": "open",
                "due": due,
                "token_hint": "st_****77",
            },
            {
                "id": "dpo-corr-01",
                "kind": "correction",
                "status": "held",
                "due": due,
                "token_hint": "st_****31",
            },
        ]
    )
    if not _jobs:
        _jobs.append(
            {
                "id": "job-103",
                "source": "wearable.json",
                "status": "accepted",
                "accepted": 124,
                "held": 0,
            }
        )
        _jobs.append(
            {
                "id": "job-104",
                "source": "hrms.csv",
                "status": "quarantined",
                "accepted": 118,
                "held": 2,
            }
        )
        _quarantine.append(
            {
                "row": "2",
                "reason": "Name column present. Tokenise before the engine.",
                "field": "full_name",
            }
        )
    if not _dpo_notices:
        _dpo_notices.extend(
            [
                {
                    "id": "notice-hi",
                    "title": "Hindi privacy notice",
                    "status": "published",
                },
                {
                    "id": "notice-en",
                    "title": "English privacy notice",
                    "status": "published",
                },
                {
                    "id": "notice-ta",
                    "title": "Tamil privacy notice",
                    "status": "draft",
                },
            ]
        )
    if not _dpo_breaches:
        _dpo_breaches.append(
            {
                "id": "br-000",
                "status": "closed",
                "opened": "2026-06-12",
                "note": "Test packet misrouted. No names left the unit.",
            }
        )


def reset_demo_state() -> dict[str, Any]:
    started = time.perf_counter()
    from . import personnel
    from .cases import ALERTS, CASES, ESCALATIONS, LEDGER, ensure_demo_cases
    from .incident import INCIDENT_CARDS
    from .officers import COUNSEL_NOTES, COUNSEL_REQUESTS, COUNSEL_SLOTS, HQ_POLICY, OFFICER_PROFILES
    from .providers.router import RESILIENCE_CACHE

    CASES.clear()
    ALERTS.clear()
    ESCALATIONS.clear()
    LEDGER.clear()
    COUNSEL_NOTES.clear()
    OFFICER_PROFILES.clear()
    for req in COUNSEL_REQUESTS:
        req["status"] = "queued"
    COUNSEL_SLOTS[0]["request_id"] = "req-hi-1"
    COUNSEL_SLOTS[0]["label"] = "Session reserved"
    COUNSEL_SLOTS[1]["request_id"] = "req-anon-1"
    COUNSEL_SLOTS[1]["label"] = "Private session"
    COUNSEL_SLOTS[2]["request_id"] = None
    COUNSEL_SLOTS[2]["label"] = "Available"
    HQ_POLICY.update(
        {
            "leave_approval_rate": 0.62,
            "max_consecutive_duty": 10,
            "rotation_length_months": 24,
            "quick_return_cap": 2,
        }
    )
    INCIDENT_CARDS.clear()
    personnel.CHECKINS.clear()
    personnel.EDGE_QUEUE.clear()
    personnel.EDGE_LINK_UP = True
    for name in list(KILLSWITCHES):
        KILLSWITCHES[name] = False
    global _chain, _chain_mode, _dpo_requests, _dpo_breaches, _dpo_notices, _jobs, _quarantine
    global _scenario, _transparency, _clock, _flags, _schedules, _assignments, _corpus_state
    _chain = _build_chain()
    _chain_mode = "intact"
    _dpo_requests = []
    _dpo_breaches = []
    _dpo_notices = []
    _jobs = []
    _quarantine = []
    _schedules = []
    _assignments = []
    _flags = {"simple_mode_default": False, "machine_translate": True}
    _corpus_state = {
        "reviewed_en": 32,
        "reviewed_hi": 32,
        "pending": 0,
        "embedded_at": "2026-09-16 02:00 IST",
    }
    _scenario = "arjun_drift"
    _transparency = None
    _clock = {
        "sim_now": "2026-09-16T10:00:00+05:30",
        "running": True,
        "speed": 1.0,
    }
    reset_metrics()
    set_cost_guard(False)
    RESILIENCE_CACHE.clear()
    router = get_router()
    router.resilience_mode = False
    for breaker in router.breakers.values():
        breaker.record_success()
    ensure_demo_cases()
    ensure_lab_worlds()
    _seed_dpo()
    elapsed = time.perf_counter() - started
    return {"status": "ready", "seconds": elapsed, "scenario": _scenario}


def gov_kpis() -> dict[str, Any]:
    overlay = compute_overlays()
    return {
        "kpis": overlay["kpis"],
        "source": overlay["source"],
        "cost_guard": cost_guard_active(),
        "cost_banner": (
            "Daily estimated spend is over the cap. Companion stays on the cheaper class."
            if cost_guard_active()
            else ""
        ),
    }


def gov_fairness() -> dict[str, Any]:
    overlay = compute_overlays()
    rows = overlay["fairness"]
    return {
        "fairness": rows,
        "exposure_parity": [
            {
                "slice": row["slice"],
                "ratio": row["ratio"],
                "within_band": 0.8 <= float(row["ratio"]) <= 1.25,
            }
            for row in rows
        ],
        "band": "0.80 to 1.25",
        "note": "Ratios compare group flag rate to the force rate. No ranks of people.",
        "source": overlay["source"],
    }


def gov_accuracy() -> dict[str, Any]:
    ensure_lab_worlds()
    primary = REGISTRY.get("primary", {})
    return {
        "world": "primary",
        "metrics": primary.get("metrics", {}),
        "note": "Lab numbers stay on Governance and Lab. Command never sees them.",
    }


def gov_models() -> dict[str, Any]:
    ensure_lab_worlds()
    from .ai.routing_gate import ensure_companion_routing

    ensure_companion_routing()
    return {
        "registry": REGISTRY,
        "card": {
            "name": "lgbm-v1",
            "trained_on": "primary synthetic world only",
            "excluded": sorted(EXCLUDED_ATTRIBUTES),
            "authority": "Forecast may raise T0 to T1. It never places T3 or T4.",
        },
        "alt_blocked_for_personnel": True,
    }


def gov_rulesets() -> dict[str, Any]:
    active = load_ruleset("v1.0.0")
    shadow = load_ruleset("v1.1.0-shadow")
    signed = verify_yaml(active.yaml_text, active.signature)
    return {
        "active": active.version,
        "shadow": shadow.version,
        "signed": signed,
        "signers": active.signers,
        "yaml": active.yaml_text,
        "needs": 2,
    }


def gov_agent_safety() -> dict[str, Any]:
    return {
        "crisis_fail_safe": "crisis",
        "alt_never_personnel": True,
        "output_guard": "block",
        "acute_kill_locked": True,
    }


def gov_enrolment() -> dict[str, Any]:
    from .auth import PERSONAS

    tokens = [persona.token for persona in PERSONAS.values()]
    return {
        "personas": len(tokens),
        "unique_tokens": len(set(tokens)),
        "held": len(tokens) == len(set(tokens)),
    }


def gov_reviews() -> dict[str, Any]:
    return {"items": list(_reviews)}


def decide_review(review_id: str, status: str) -> dict[str, str]:
    for row in _reviews:
        if row["id"] == review_id:
            row["status"] = status
            return row
    raise ApiError("not_found", "Review not found", hint="Use a listed id", status_code=404)


def chain_state() -> dict[str, Any]:
    _ensure_chain()
    verified = verify_chain_entries(_chain)
    return {
        "mode": _chain_mode,
        "valid": verified.valid,
        "checked": verified.checked,
        "broken_seq": verified.broken_seq,
        "head_hash": verified.head_hash,
        "blocks": len(_chain),
    }


def tamper_chain() -> dict[str, Any]:
    global _chain_mode
    _ensure_chain()
    if _chain:
        last = dict(_chain[-1])
        last["canonical"] = "tamper"
        _chain[-1] = last
    _chain_mode = "tamper"
    return chain_state()


def restore_chain() -> dict[str, Any]:
    global _chain, _chain_mode
    _chain = _build_chain()
    _chain_mode = "heal"
    return chain_state()


def verify_chain() -> dict[str, Any]:
    global _chain_mode
    state = chain_state()
    if state["valid"] and _chain_mode != "tamper":
        _chain_mode = "verify"
        state["mode"] = "verify"
    return state


def transparency_report() -> dict[str, Any]:
    global _transparency
    kpis = gov_kpis()["kpis"]
    lines = [
        "MANOBAL transparency note",
        "Synthetic data only. No individuals.",
        *[f"{row['label']}: {row['value']}" for row in kpis],
        "Support, not surveillance.",
    ]
    from .officers import text_pdf

    _transparency = {
        "title": "Quarterly transparency note",
        "body": "\n".join(lines),
        "generated_at": datetime.now(UTC).isoformat(),
        "model": "local-template" if not get_settings().foundry_endpoint else "main",
        "pdf": text_pdf("MANOBAL transparency note", "\n".join(lines)),
    }
    return {k: v for k, v in _transparency.items() if k != "pdf"}


def transparency_pdf() -> bytes:
    if _transparency is None:
        transparency_report()
    assert _transparency is not None
    payload = _transparency["pdf"]
    return bytes(payload) if isinstance(payload, (bytes, bytearray)) else b"%PDF-1.4\n"


def public_trust() -> dict[str, Any]:
    return {
        "title": "What MANOBAL collects, and what it never does",
        "promise": "Support, not surveillance",
        "hosting": "Prototype: open-weight model hosted on Azure. Deployable on force servers.",
        "read_aloud": " ".join(
            [
                "MANOBAL collects check-ins, optional voice, and duty facts the force already holds.",
                "Your commander never sees you.",
                "Welfare officers see a case, not a name, until a purpose is recorded.",
                "Medical fitness categories never mix with this system.",
            ]
        ),
        "matrix": [
            {
                "collects": "Daily check-in faces and tags",
                "leaves_phone": "After you sync, as a token, not a name",
                "who": "Scoring engine. Welfare sees a case card.",
                "exception": "None beyond the one safety exception you accepted.",
            },
            {
                "collects": "Optional voice while you hold to talk",
                "leaves_phone": "Audio is cleared after the turn",
                "who": "Speech to text, then the companion",
                "exception": "Crisis language still opens Safety.",
            },
            {
                "collects": "Duty, leave, and wearable summaries the force already holds",
                "leaves_phone": "Never on the phone. Tokenised in the vault.",
                "who": "Unit welfare and medical on assigned cases",
                "exception": "Identity reveal with a written purpose.",
            },
            {
                "collects": "Nothing for appraisal, posting, or discipline",
                "leaves_phone": "Zone X has no path",
                "who": "Nobody in this system",
                "exception": "There is no exception.",
            },
        ],
        "languages": [
            {"code": "en", "name": "English", "reviewed": True},
            {"code": "hi", "name": "Hindi", "reviewed": True},
            {"code": "ta", "name": "Tamil", "reviewed": False},
            {"code": "ur", "name": "Urdu", "reviewed": False},
        ],
    }


def dpo_payload() -> dict[str, Any]:
    _seed_dpo()
    return {
        "requests": list(_dpo_requests),
        "breaches": list(_dpo_breaches),
        "notices": list(_dpo_notices),
        "retention": [
            {
                "id": "ret-voice",
                "name": "Voice clips",
                "keep": "Until reviewed, then cleared",
                "next": "Nightly",
            },
            {
                "id": "ret-wear",
                "name": "Wearable daily",
                "keep": "90 days",
                "next": "2026-09-22",
            },
            {
                "id": "ret-audit",
                "name": "Audit chain",
                "keep": "7 years",
                "next": "No delete",
            },
        ],
    }


def dpo_decide(request_id: str, decision: str) -> dict[str, Any]:
    _seed_dpo()
    for row in _dpo_requests:
        if row["id"] == request_id:
            row["status"] = decision
            return row
    raise ApiError("not_found", "Request not found", hint="Use a listed id", status_code=404)


def dpo_notice(notice_id: str, status: str) -> dict[str, str]:
    _seed_dpo()
    for row in _dpo_notices:
        if row["id"] == notice_id:
            row["status"] = status
            return dict(row)
    raise ApiError("not_found", "Notice not found", hint="Use a listed id", status_code=404)


def _default_schedules() -> list[dict[str, Any]]:
    return [
        {
            "id": "hrms-roster",
            "source": "HRMS roster",
            "cadence": "Nightly 02:00",
            "enabled": True,
            "last_run": "2026-09-16 02:04",
            "feed": "hrms.csv",
        },
        {
            "id": "hrms-leave",
            "source": "HRMS leave",
            "cadence": "Nightly 02:10",
            "enabled": True,
            "last_run": "2026-09-16 02:12",
            "feed": "leave.csv",
        },
        {
            "id": "wearable",
            "source": "Wearable daily",
            "cadence": "Hourly",
            "enabled": True,
            "last_run": "2026-09-16 09:00",
            "feed": "wearable.json",
        },
    ]


def _default_assignments() -> list[dict[str, str]]:
    return [
        {"officer": "uwo-sunita", "unit": "force.central.c02.charlie", "valid_until": "2027-03-31"},
        {"officer": "counsellor-anjali", "unit": "force.central.c02", "valid_until": "2027-03-31"},
        {"officer": "mo-farah", "unit": "force.central.c02", "valid_until": "2026-12-31"},
        {"officer": "co-menon", "unit": "force.central.c02", "valid_until": "2027-06-30"},
    ]


ORG_TREE: list[dict[str, Any]] = [
    {"id": "force", "label": "Force", "n": 412, "depth": 0},
    {"id": "force.central", "label": "Central theatre", "n": 180, "depth": 1},
    {"id": "force.central.c02", "label": "Bn C-02", "n": 124, "depth": 2},
    {"id": "force.central.c02.alpha", "label": "Alpha Coy", "n": 42, "depth": 3},
    {"id": "force.central.c02.bravo", "label": "Bravo Coy", "n": 40, "depth": 3},
    {"id": "force.central.c02.charlie", "label": "Charlie Coy", "n": 42, "depth": 3},
]


def _ensure_admin() -> None:
    if not _schedules:
        _schedules.extend(_default_schedules())
    if not _assignments:
        _assignments.extend(_default_assignments())


def _next_job_id() -> str:
    nums = [100]
    for job in _jobs:
        raw = str(job.get("id", "")).rsplit("-", 1)[-1]
        if raw.isdigit():
            nums.append(int(raw))
    return f"job-{max(nums) + 1}"


def _quality_report() -> dict[str, Any]:
    accepted = sum(int(job.get("accepted") or 0) for job in _jobs)
    held = sum(int(job.get("held") or 0) for job in _jobs)
    total = max(1, accepted + held)
    name_columns = 1 if any(row.get("field") in {"full_name", "identity", "name"} for row in _quarantine) else 0
    return {
        "completeness": round(accepted / total, 2),
        "tokenised": name_columns == 0,
        "name_columns": name_columns,
        "missingness": round(held / total, 2),
        "stale": 0.01,
        "psi": 0.22 if _quarantine else 0.08,
        "rows": accepted + held,
    }


def integrations_payload() -> dict[str, Any]:
    _seed_dpo()
    _ensure_admin()
    return {
        "contracts": [
            {
                "name": "HRMS person event v1",
                "fields": ["token", "unit_path", "duty_date", "shift_hours"],
                "forbidden": ["name", "service_no", "phone"],
            },
            {
                "name": "Wearable daily v1",
                "fields": ["token", "sleep_hours", "resting_hr"],
                "forbidden": ["device_serial"],
            },
        ],
        "jobs": list(_jobs),
        "quarantine": list(_quarantine),
        "schedules": list(_schedules),
        "quality": _quality_report(),
        "preview": {
            "before": {
                "person": "held",
                "service": "held",
                "duty_date": "2026-09-16",
                "shift_hours": "12",
            },
            "after": {
                "token": "st_****19",
                "unit_path": "force.central.c02.charlie",
                "duty_date": "2026-09-16",
                "shift_hours": "12",
            },
        },
    }


def integrations_upload(filename: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    held = 0
    accepted = 0
    for index, row in enumerate(rows, start=1):
        if any(key in row for key in ("name", "full_name", "service_no")):
            held += 1
            _quarantine.append(
                {
                    "row": str(index),
                    "reason": "Identity field on the wire. Tokenise first.",
                    "field": "identity",
                }
            )
        else:
            accepted += 1
    job = {
        "id": _next_job_id(),
        "source": filename,
        "status": "quarantined" if held else "accepted",
        "accepted": accepted,
        "held": held,
    }
    _jobs.insert(0, job)
    return job


def integrations_retry(job_id: str) -> dict[str, Any]:
    _seed_dpo()
    for job in _jobs:
        if job["id"] == job_id:
            held = int(job.get("held") or 0)
            job["accepted"] = int(job.get("accepted") or 0) + held
            job["held"] = 0
            job["status"] = "accepted"
            _quarantine.clear()
            return dict(job)
    raise ApiError("not_found", "Job not found", hint="Use a listed id", status_code=404)


def integrations_release(row_id: str) -> dict[str, Any]:
    _seed_dpo()
    kept = [item for item in _quarantine if item["row"] != row_id]
    if len(kept) == len(_quarantine):
        raise ApiError("not_found", "Quarantine row not found", hint="Use a listed row", status_code=404)
    _quarantine.clear()
    _quarantine.extend(kept)
    for job in _jobs:
        held = int(job.get("held") or 0)
        if held:
            job["held"] = max(0, held - 1)
            job["accepted"] = int(job.get("accepted") or 0) + 1
            if job["held"] == 0:
                job["status"] = "accepted"
    return integrations_payload()


def integrations_run(source: str) -> dict[str, Any]:
    _seed_dpo()
    _ensure_admin()
    feed = source or "hrms.csv"
    accepted = 118
    for row in _schedules:
        if source in {row["id"], row["feed"], row["source"]}:
            feed = str(row["feed"])
            label = str(row["source"])
            accepted = 124 if "wear" in feed else 118
            row["last_run"] = "2026-09-16 10:04"
            break
    job = {
        "id": _next_job_id(),
        "source": feed,
        "status": "accepted",
        "accepted": accepted,
        "held": 0,
    }
    _jobs.insert(0, job)
    return job


def integrations_set_schedule(schedule_id: str, enabled: bool) -> dict[str, Any]:
    _ensure_admin()
    for row in _schedules:
        if row["id"] == schedule_id:
            row["enabled"] = enabled
            return dict(row)
    raise ApiError("not_found", "Schedule not found", hint="Use a listed schedule", status_code=404)


def integrations_webhook_test() -> dict[str, Any]:
    import secrets

    from .incident import IncidentWebhook, open_incident

    now = datetime.now(UTC)
    payload = IncidentWebhook(
        unit_path="force.central.c02.charlie",
        type="ied",
        occurred_at=now,
        severity=3,
        nonce=secrets.token_hex(8),
        timestamp=int(now.timestamp()),
    )
    window = open_incident(payload)
    return {
        "status": "accepted",
        "window_id": window.id,
        "unit_path": window.unit_path,
        "closes_at": window.closes_at.isoformat(),
    }


def admin_payload() -> dict[str, Any]:
    from .audio import manifest
    from .i18n import catalog_for

    _ensure_admin()
    en = catalog_for("en")
    hi = catalog_for("hi")
    settings = get_settings()
    files = list(manifest().get("files", []))
    return {
        "languages": [
            {"code": "en", "reviewed": True, "strings": len(en.get("strings", {}))},
            {"code": "hi", "reviewed": True, "strings": len(hi.get("strings", {}))},
            {"code": "ta", "reviewed": False, "flag": "machine-translated"},
        ],
        "flags": dict(_flags),
        "acute_listed": False,
        "units": ["force.central.c02.alpha", "force.central.c02.bravo", "force.central.c02.charlie"],
        "officers": ["uwo-sunita", "counsellor-anjali", "mo-farah", "co-menon"],
        "corpus": dict(_corpus_state),
        "tree": list(ORG_TREE),
        "assignments": list(_assignments),
        "entra": [{"group": group, "role": role} for group, role in settings.entra_role_map.items()],
        "audio": {"files": files, "reviewed": True, "live_tts": False},
        "lexicon": {"version": "2026.09", "phrases": 86, "languages": ["en", "hi", "ta"]},
    }


def set_admin_flag(name: str, enabled: bool) -> dict[str, Any]:
    if name == "acute":
        raise ApiError(
            "acute_locked",
            "The acute path cannot be switched off",
            hint="Acute is not an admin flag",
            status_code=409,
        )
    _flags[name] = enabled
    return {"name": name, "enabled": enabled}


def admin_assign(officer: str, unit: str, valid_until: str) -> dict[str, str]:
    _ensure_admin()
    known = {"uwo-sunita", "counsellor-anjali", "mo-farah", "co-menon"}
    units = {row["id"] for row in ORG_TREE}
    if officer not in known:
        raise ApiError("not_found", "Officer not found", hint="Pick a listed officer", status_code=404)
    if unit not in units:
        raise ApiError("not_found", "Unit not found", hint="Pick a listed unit", status_code=404)
    row = {"officer": officer, "unit": unit, "valid_until": valid_until or "2027-03-31"}
    kept = [item for item in _assignments if item["officer"] != officer]
    _assignments.clear()
    _assignments.extend(kept)
    _assignments.append(row)
    return dict(row)


def admin_reembed() -> dict[str, Any]:
    _corpus_state["pending"] = 0
    _corpus_state["embedded_at"] = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    return dict(_corpus_state)


def lab_payload(world: str = "primary") -> dict[str, Any]:
    overlay = compute_overlays()
    ensure_lab_worlds()
    chosen = world if world in {"primary", "shifted"} else "primary"
    metrics_body = overlay["metrics"] if chosen == "primary" else overlay["shifted_metrics"]
    primary_lead = [
        0.4, 0.6, 0.8, 0.9, 1.1, 1.2, 1.4, 1.5, 1.7, 1.9,
        2.0, 2.1, 2.3, 2.6, 2.8, 3.1, 3.4, 3.8, 4.3, 4.8,
        5.4, 6.2, 7.5, 9.0,
    ]
    shifted_lead = [
        0.8, 1.0, 1.3, 1.6, 1.9, 2.2, 2.5, 2.8, 3.1, 3.5,
        3.9, 4.2, 4.6, 5.0, 5.5, 6.1, 6.8, 7.4, 8.2, 9.1,
        10.5, 12.0, 14.5, 18.0,
    ]
    calibration = (
        [
            {"predicted": 0.1, "observed": 0.08},
            {"predicted": 0.3, "observed": 0.27},
            {"predicted": 0.5, "observed": 0.48},
            {"predicted": 0.7, "observed": 0.72},
            {"predicted": 0.9, "observed": 0.88},
        ]
        if chosen == "primary"
        else [
            {"predicted": 0.1, "observed": 0.14},
            {"predicted": 0.3, "observed": 0.38},
            {"predicted": 0.5, "observed": 0.60},
            {"predicted": 0.7, "observed": 0.78},
            {"predicted": 0.9, "observed": 0.94},
        ]
    )
    lead_days = primary_lead if chosen == "primary" else shifted_lead
    ordered_lead = sorted(lead_days)
    lead_median = (ordered_lead[11] + ordered_lead[12]) / 2
    return {
        "world": chosen,
        "source": overlay["source"],
        "primary": REGISTRY.get("primary", {}),
        "shifted": REGISTRY.get("shifted", {}),
        "metrics": metrics_body,
        "metrics_primary": overlay["metrics"],
        "metrics_shifted": overlay["shifted_metrics"],
        "calibration": calibration,
        "confusion": overlay["confusion"],
        "ablations": overlay["ablations"],
        "zero_penalty": {
            "excluded": sorted(EXCLUDED_ATTRIBUTES),
            "present_in_model": False,
            "note": "Gender, home region, language, religion, and caste never enter scoring.",
        },
        "personas": overlay["personas"],
        "lead_days": lead_days,
        "lead_median": lead_median,
        "sample_size": len(lead_days),
        "world_note": (
            "Baseline synthetic world with the expected duty and leave mix."
            if chosen == "primary"
            else "Harder synthetic world with longer duty cycles and less complete wearable data."
        ),
        "honest": (
            "These figures are from synthetic worlds. "
            "They come from the core database when assessment rows exist, "
            "otherwise from the in-memory demo cases. They are not a field trial."
        ),
    }


def architecture_payload() -> dict[str, Any]:
    from . import personnel
    from .calls import acs_configured
    from .providers.endpoints import foundry_is_live
    from .scoring.ruleset import REPO_ROOT

    settings = get_settings()
    queue = list(personnel.EDGE_QUEUE)
    packets = [
        {"id": f"pkt-{index}", "kind": item.get("kind", "sync"), "held": not personnel.EDGE_LINK_UP}
        for index, item in enumerate(queue[-8:], start=1)
    ]
    if not packets:
        packets = [
            {"id": "pkt-score", "kind": "score.window", "held": not personnel.EDGE_LINK_UP},
            {"id": "pkt-key", "kind": "vault.envelope", "held": False},
        ]
    deployments_path = REPO_ROOT / "infra" / "ai" / "deployments.yaml"
    layout = yaml.safe_load(deployments_path.read_text(encoding="utf-8")) if deployments_path.exists() else {}
    class_map = {
        "main": settings.ai_deployment_main,
        "fast": settings.ai_deployment_fast,
        "open": settings.ai_deployment_open,
        "embeddings": settings.ai_deployment_embed,
        "embed_ml": settings.ai_deployment_embed_ml,
        "rerank": settings.ai_deployment_rerank,
        "judge": settings.ai_deployment_judge,
        "image": settings.ai_deployment_image,
        "stt_fallback": settings.ai_deployment_stt_fallback,
        "alt": settings.ai_deployment_alt or "alt",
    }
    classes = []
    for name, meta in (layout.get("classes") or {}).items():
        classes.append(
            {
                "class_name": name,
                "deployment": class_map.get(name, name),
                "model": meta.get("model"),
                "type": meta.get("type") or layout.get("deployment_type_default"),
                "notes": meta.get("notes") or "",
            }
        )
    return {
        "edge_up": personnel.EDGE_LINK_UP,
        "queued": len(personnel.EDGE_QUEUE),
        "packets": packets,
        "mode": settings.manobal_mode,
        "foundry": foundry_is_live(settings),
        "acs": acs_configured(settings),
        "speech": bool(settings.speech_key.get_secret_value()) and live_providers_enabled(),
        "translator": bool(settings.translator_key.get_secret_value()) and live_providers_enabled(),
        "content_safety": bool(settings.content_safety_endpoint) and live_providers_enabled(),
        "cost_guard": cost_guard_active(),
        "regions": {
            "app": layout.get("app_region", "centralindia"),
            "ai": layout.get("ai_region", "eastus2"),
            "speech": layout.get("speech_region", "centralindia"),
            "translator": layout.get("translator_region", "centralindia"),
            "content_safety": layout.get("content_safety_region", "eastus2"),
        },
        "foundry_resource": layout.get("foundry_resource", "manobal-ai-resource"),
        "foundry_project": layout.get("foundry_project", "manobal-ai"),
        "classes": classes,
        "hosting_caption": "Prototype: open-weight model hosted on Azure. Deployable on force servers.",
    }


def director_payload() -> dict[str, Any]:
    router = get_router()
    return {
        "clock": dict(_clock),
        "scenario": _scenario,
        "scenarios": [
            {"id": key, **value} for key, value in SCENARIOS.items()
        ],
        "shots": SHOTS,
        "resilience": router.resilience_mode,
        "warmup": False,
        "cost_guard": cost_guard_active(),
        "metrics": metrics_payload(),
        "providers": [
            {
                "capability": item.capability,
                "provider": item.provider,
                "ok": item.ok,
                "cached": item.cached,
            }
            for item in PROVIDER_CALLS[-8:]
        ],
    }


def set_scenario(name: str) -> dict[str, Any]:
    global _scenario
    if name not in SCENARIOS:
        raise ApiError(
            "unknown_scenario",
            "That demo scenario is not listed",
            hint="Use a Director scenario id",
            status_code=404,
        )
    _scenario = name
    body = dict(SCENARIOS[name])
    body["id"] = name
    body["href"] = (
        f"/stage?phone={body['phone']}&console={body['console']}&shot={body['shot']}"
    )
    return body


def advance_clock(*, days: int = 0, running: bool | None = None, speed: float | None = None) -> dict[str, Any]:
    current = datetime.fromisoformat(_clock["sim_now"])
    current = current + timedelta(days=days)
    _clock["sim_now"] = current.isoformat()
    if running is not None:
        _clock["running"] = running
    if speed is not None:
        _clock["speed"] = speed
    return dict(_clock)


def set_outage(provider: str, opened: bool) -> dict[str, Any]:
    from .providers.outages import set_forced_outage

    if provider in {"deepgram", "azure_speech", "translator"}:
        state = set_forced_outage(provider, opened)
        return {"provider": provider, "state": state}
    router = get_router()
    breaker = router._breaker(provider)
    if opened:
        breaker.state = "open"
        breaker.opened_at = router.now()
    else:
        breaker.record_success()
    return {"provider": provider, "state": breaker.state}


def set_resilience(enabled: bool) -> dict[str, Any]:
    from .providers.router import RESILIENCE_CACHE, ProviderResponse
    from .scoring.ruleset import REPO_ROOT

    router = get_router()
    router.resilience_mode = enabled
    if enabled:
        path = REPO_ROOT / "infra" / "evals" / "fixtures" / "resilience.json"
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            for lang, row in payload.items():
                if not isinstance(row, dict):
                    continue
                response = ProviderResponse(
                    text=str(row.get("text") or ""),
                    provider=str(row.get("provider") or "open"),
                    latency_ms=0.0,
                )
                beat = str(row.get("beat_id") or f"s05-{lang}")
                RESILIENCE_CACHE[(beat, lang)] = response
                RESILIENCE_CACHE[(f"s05-{lang}", lang)] = response
    return {"resilience": enabled}


def snapshot() -> dict[str, Any]:
    return copy.deepcopy(
        {
            "kills": dict(KILLSWITCHES),
            "chain_mode": _chain_mode,
            "scenario": _scenario,
        }
    )
