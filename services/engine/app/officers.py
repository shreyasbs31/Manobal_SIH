from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from .auth import PERSONAS
from .cases import CASES, LEDGER
from .levers import rank_levers
from .privacy.kanon import complementary_suppress, commander_incident_card, simulator_allows
from .privacy.rights import contact_note_due, write_contact_note

INDIVIDUAL_RE = re.compile(
    r"who is|named|token|mb-\d|this person|jawan|constable|kaun|pareshan|naam|vyakti",
    re.I,
)


def chime_kind_for_queue(t4_count: int, t3_count: int) -> str:
    if t4_count > 0:
        return "t4"
    if t3_count > 0:
        return "t3"
    return ""

OFFICER_PROFILES: dict[str, dict[str, Any]] = {}

_DEFAULTS: dict[str, dict[str, Any]] = {
    "uwo-sunita": {
        "brief_language": "hi",
        "opener_tone": "informal",
        "digest_time": "08:00",
        "queue_preset": "sla",
        "saved_lever_notes": [],
    },
    "counsellor-anjali": {
        "languages": ["hi", "mr", "en"],
        "availability": ["09:00-13:00", "15:00-18:00"],
        "session_types": ["anonymous", "named", "voice", "video"],
        "load": 4,
    },
    "mo-farah": {
        "escalation_contacts": ["battalion_mo", "sector_counsellor"],
        "on_call": ["Mon", "Wed", "Fri"],
    },
    "commander-menon": {
        "pinned_kpis": ["duty_hours", "night_load", "leave_backlog"],
        "theatre": "lwe",
        "copilot_language": "hi",
        "brief_time": "Monday 09:00",
        "default_unit": "force.central.c02",
    },
    "hq-central": {
        "policy_lens": "rotation_length",
        "comparison_set": ["central", "north", "east", "capital"],
    },
    "wdec-kavita": {
        "watchlists": ["gate_hit_rates"],
    },
}

COUNSEL_NOTES: dict[str, str] = {}
COUNSEL_REQUESTS: list[dict[str, Any]] = [
    {
        "id": "req-hi-1",
        "kind": "named",
        "language": "hi",
        "handle": None,
        "status": "queued",
        "summary": "Leave and rest, Hindi.",
    },
    {
        "id": "req-anon-1",
        "kind": "anonymous",
        "language": "en",
        "handle": "River-17",
        "status": "queued",
        "summary": "Anonymous check-in slot.",
    },
]
COUNSEL_SUGGESTIONS: list[dict[str, str]] = []
CASE_ACTIONS: list[dict[str, str]] = []
HQ_BRIEF = {
    "title": "Monthly welfare brief, Sector Central",
    "body": (
        "Leave backlog is high in the north theatre [leave_backlog]. "
        "Charlie Coy duty hours sit above the usual band [duty_hours]. "
        "Lever REST_48H is associated with later easing in similar weeks "
        "[lever_rest_48h]. This is observational, not causal."
    ),
    "edited": False,
}


def officer_profile(actor_id: str) -> dict[str, Any]:
    if actor_id not in OFFICER_PROFILES:
        base = dict(_DEFAULTS.get(actor_id) or {})
        OFFICER_PROFILES[actor_id] = base
    return dict(OFFICER_PROFILES[actor_id])


def patch_officer_profile(actor_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    current = officer_profile(actor_id)
    current.update(patch)
    OFFICER_PROFILES[actor_id] = current
    return dict(current)


def match_counsellor(language: str) -> dict[str, Any]:
    wanted = language.lower()
    ranked = []
    for actor_id, defaults in _DEFAULTS.items():
        langs = [str(item).lower() for item in defaults.get("languages") or []]
        if not langs:
            continue
        load = int(defaults.get("load") or 0)
        score = 0 if wanted in langs else 10
        ranked.append((score, load, actor_id, langs))
    ranked.sort()
    if not ranked:
        return {"counsellor": "counsellor-anjali", "languages": ["hi", "mr", "en"]}
    _score, _load, actor_id, langs = ranked[0]
    return {"counsellor": actor_id, "languages": langs, "matched": wanted in langs}


def welfare_tabs(scope_path: str) -> dict[str, Any]:
    from .cases import digest_items, queue_items
    from .incident import uwo_board

    open_cases = [case for case in queue_items(scope_path) if case.status != "closed"]
    t4 = [case.case_id for case in open_cases if case.tier == "T4"]
    t3 = [case.case_id for case in open_cases if case.tier == "T3"]
    digest = [case.case_id for case in digest_items()]
    followups = [
        {"case_id": "MB-4091", "due": "D+2", "reason": "REST_48H check"},
    ]
    self_referrals = [
        {"case_id": "MB-5120", "channel": "I want to talk", "status": "open"},
    ]
    closed = [case.case_id for case in CASES.values() if case.status == "closed"]
    return {
        "open": len(open_cases),
        "overdue": 1 if t4 else 0,
        "capacity": 25,
        "load": len(open_cases),
        "t4": t4,
        "t3": t3,
        "digest": digest,
        "incidents": uwo_board(scope_path),
        "self_referrals": self_referrals,
        "followups": followups,
        "closed": closed,
        "grievances": [{"category": "Land or property", "open": 1}],
        "workload": [8, 11, 14, len(open_cases)],
    }


def reveal_identity(
    *,
    case_id: str,
    actor: str,
    purpose_code: str,
    justification: str,
) -> dict[str, Any]:
    if len(justification.strip()) < 8:
        raise ValueError("justification")
    if purpose_code not in {"care_contact", "urgent_welfare", "follow_up"}:
        raise ValueError("purpose")
    case = CASES.get(case_id)
    if case is None:
        raise KeyError(case_id)
    grant_id = hashlib.sha256(f"{case_id}:{actor}:{purpose_code}".encode()).hexdigest()[:16]
    due = datetime.now(UTC) + timedelta(hours=24)
    LEDGER.append(
        {
            "token": case.token,
            "actor": actor,
            "actor_label": "Welfare Officer, your unit, viewed your identity",
            "action": "identity.viewed",
            "purpose_code": purpose_code,
            "at": datetime.now(UTC).isoformat(),
        }
    )
    contact_note_due(grant_id, due.isoformat())
    persona = next((item for item in PERSONAS.values() if item.case_id == case_id), None)
    return {
        "revealed": True,
        "grant_id": grant_id,
        "contact_note_due": due.isoformat(),
        "notice": "This person will see that you viewed their identity.",
        "card": {
            "synthetic": True,
            "label": persona.display_label if persona else "Synthetic person",
            "rank": "Constable/GD",
            "unit": "Charlie Coy, Bn C-02",
            "contact": "Unit welfare line",
            "posting": "Central",
            "case_id": case_id,
        },
    }


def save_contact_note(grant_id: str, note: str) -> dict[str, str]:
    write_contact_note(grant_id, note)
    return {"grant_id": grant_id, "status": "noted"}


def record_case_action(
    case_id: str,
    *,
    mode: str,
    lever: str,
    outcome: str,
    follow_up: str,
    refer: str,
) -> dict[str, str]:
    row = {
        "case_id": case_id,
        "mode": mode,
        "lever": lever,
        "outcome": outcome,
        "follow_up": follow_up,
        "refer": refer,
        "at": datetime.now(UTC).isoformat(),
    }
    CASE_ACTIONS.append(row)
    if case_id in CASES and outcome in {"closed", "resolved"}:
        CASES[case_id].status = "closed"
    LEDGER.append(
        {
            "token": CASES[case_id].token if case_id in CASES else "",
            "actor_label": "Welfare Officer, your unit",
            "action": "case.action",
            "purpose_code": lever or "care",
            "at": row["at"],
        }
    )
    return row


def case_brief_fields(case_id: str) -> dict[str, str]:
    case = CASES[case_id]
    levers = rank_levers(
        tier=case.tier,
        dominant_domains=case.dominant_domains,
        lifecycle_state="inducted",
    )
    return {
        "tier": case.tier,
        "domain": case.dominant_domains[0] if case.dominant_domains else "workload",
        "onset": "about 20 days",
        "lever": levers[0].code if levers else "REST_48H",
        "drift": "Drift began about 20 days ago",
    }


def command_posture_payload() -> dict[str, Any]:
    companies = ["Alpha Coy", "Bravo Coy", "Charlie Coy", "Post D-7", "Delta Coy"]
    weeks = 12
    raw_cells: list[dict[str, Any]] = []
    for company in companies:
        for week in range(1, weeks + 1):
            n = 7 if company == "Post D-7" else 8 if company == "Delta Coy" and week > 7 else 40
            rising = company == "Charlie Coy" and week > 8
            raw_cells.append(
                {
                    "key": f"{company}:{week}",
                    "unit": company,
                    "week": week,
                    "n": n,
                    "band": "T2" if rising else "T0",
                    "shareLabel": "20 to 30%" if rising else "under 10%",
                }
            )
    cells = complementary_suppress(raw_cells, k=10)
    public_cells = []
    for cell in cells:
        item: dict[str, Any] = {
            "unit": cell.get("unit"),
            "week": cell.get("week"),
            "band": cell.get("band", "hidden"),
        }
        if cell.get("band") != "hidden" and cell.get("shareLabel"):
            item["shareLabel"] = cell["shareLabel"]
        public_cells.append(item)
    return {
        "unit_label": "Bn C-02",
        "week": 38,
        "duty_hours": "61",
        "rest_denials": "14",
        "night_load": "38%",
        "quick_returns": "6",
        "leave_backlog": "22 days",
        "median_leave": "41 days",
        "incident_exposure": "Bravo window open",
        "grievance_age": "21 days",
        "takeaway": "Charlie Coy's workload has risen for three weeks.",
        "companies": companies,
        "cells": public_cells,
        "sparks": {
            "Alpha Coy": [4, 4, 5, 5],
            "Bravo Coy": [5, 6, 5, 6],
            "Charlie Coy": [6, 7, 8, 9],
            "Post D-7": [1, 1, 1, 1],
            "Delta Coy": [3, 3, 4, 4],
        },
        "incident": commander_incident_card(
            enrolled=100,
            asked=4,
            open_until="2026-09-16T06:00:00+00:00",
            followup="2026-10-11T06:00:00+00:00",
        ),
    }


def roster_companies() -> list[dict[str, Any]]:
    return [
        {
            "id": "alpha",
            "label": "Alpha Coy",
            "n": 42,
            "duty_hours": 54,
            "rest_days": 1.4,
            "night_share": 28,
            "quick_return_cap": 2,
            "leave_release": 3,
            "locked": False,
        },
        {
            "id": "bravo",
            "label": "Bravo Coy",
            "n": 38,
            "duty_hours": 58,
            "rest_days": 1.1,
            "night_share": 32,
            "quick_return_cap": 2,
            "leave_release": 2,
            "locked": False,
        },
        {
            "id": "charlie",
            "label": "Charlie Coy",
            "n": 44,
            "duty_hours": 61,
            "rest_days": 0.8,
            "night_share": 38,
            "quick_return_cap": 3,
            "leave_release": 1,
            "locked": False,
        },
        {
            "id": "post-d7",
            "label": "Post D-7",
            "n": 7,
            "duty_hours": 62,
            "rest_days": 0.6,
            "night_share": 40,
            "quick_return_cap": 3,
            "leave_release": 0,
            "locked": True,
            "lock_reason": "Groups under 10 cannot be simulated alone.",
        },
    ]


def project_roster(body: dict[str, Any]) -> dict[str, Any]:
    n = int(body.get("n") or 0)
    if n and not simulator_allows(n):
        raise ValueError("k_anonymity")
    companies = body.get("companies") or roster_companies()
    locked = [row for row in companies if int(row.get("n") or 0) < 10]
    projected = []
    coverage = []
    for row in companies:
        if int(row.get("n") or 0) < 10:
            projected.append(
                {"label": row["label"], "posture": "locked", "coverage": "locked"}
            )
            coverage.append({"label": row["label"], "before": "held", "after": "held"})
            continue
        duty = int(row.get("duty_hours") or 56)
        projected.append(
            {
                "label": row["label"],
                "posture": "easing" if duty <= 56 else "held high",
                "coverage": "held" if duty >= 50 else "thin",
            }
        )
        coverage.append(
            {
                "label": row["label"],
                "before": "stretched" if duty > 58 else "steady",
                "after": "steadier" if duty <= 56 else "stretched",
            }
        )
    return {
        "ok": True,
        "locked": locked,
        "horizon_days": 14,
        "posture": projected,
        "coverage": coverage,
    }


def draft_order(body: dict[str, Any]) -> dict[str, str]:
    lines = [
        "Draft company order, Bn C-02. Synthetic.",
        "MANOBAL does not issue this order. A commander reviews and signs elsewhere.",
    ]
    for row in body.get("companies") or roster_companies():
        if int(row.get("n") or 0) < 10:
            lines.append(f"{row['label']}: omitted. Group under 10.")
            continue
        lines.append(
            f"{row['label']}: weekly duty about {row.get('duty_hours')} hours, "
            f"night share {row.get('night_share')} percent, "
            f"leave release {row.get('leave_release')} a week."
        )
    return {"title": "Draft company order", "body": "\n".join(lines)}


def leave_pressure() -> dict[str, Any]:
    return {
        "copy": "MANOBAL does not submit leave. This is a release plan at company level.",
        "companies": [
            {"label": "Alpha Coy", "backlog_days": 12, "longest_wait": "18 to 30 days"},
            {"label": "Charlie Coy", "backlog_days": 22, "longest_wait": "31 to 45 days"},
        ],
        "minimum_strength": "held",
    }


def unit_climate() -> dict[str, Any]:
    return {
        "pulse": [
            {"week": "W-3", "heavy": "hidden"},
            {"week": "W-2", "heavy": "a few"},
            {"week": "W-1", "heavy": "20 to 30%"},
            {"week": "W0", "heavy": "20 to 30%"},
        ],
        "colleague_conflict": "stable, k-anonymous",
        "grievances": [
            {"category": "Leave", "age": "14 days"},
            {"category": "Land or property", "age": "60 days"},
            {"category": "Family", "age": "9 days"},
        ],
    }


def copilot_tools() -> dict[str, Any]:
    posture = command_posture_payload()
    return {
        "get_unit_metrics": {
            "duty_hours": posture["duty_hours"],
            "night_load": posture["night_load"],
            "share_t2": "20 to 30%",
        },
        "get_posture": {"takeaway": posture["takeaway"]},
        "list_top_drivers": ["Roster overtime", "Night load"],
        "get_grievance_trends": unit_climate()["grievances"],
        "simulate_roster": {"n_min": 10},
    }


def copilot_answer(question: str, lang: str = "en") -> dict[str, Any]:
    tools = copilot_tools()
    metrics = tools["get_unit_metrics"]
    if INDIVIDUAL_RE.search(question or ""):
        if lang.startswith("hi") or "kaun" in question.lower() or "pareshan" in question.lower():
            answer = (
                "Main kisi jawan ka naam nahi de sakta. "
                "Charlie Coy mein T2 ya usse upar hissa 20 se 30 pratishat hai, "
                "aur duty hours teen hafte se upar hain."
            )
        else:
            answer = (
                "I cannot name anyone in the unit. "
                "Charlie Coy share at T2 or above is 20 to 30 percent, "
                "and duty hours have been high for three weeks."
            )
        return {
            "refuse": True,
            "answer": answer,
            "chart_spec": {"type": "bar", "metric": "share_t2", "value": metrics["share_t2"]},
            "tools_used": ["get_unit_metrics", "get_posture"],
        }
    return {
        "refuse": False,
        "answer": (
            f"Charlie Coy share at T2 or above is {metrics['share_t2']}. "
            f"Duty hours {metrics['duty_hours']}, night load {metrics['night_load']}."
        ),
        "chart_spec": {"type": "bar", "metric": "duty_hours", "value": metrics["duty_hours"]},
        "tools_used": ["get_unit_metrics", "list_top_drivers"],
    }


def hq_payload() -> dict[str, Any]:
    return {
        "theatres": [
            {
                "id": "central",
                "label": "Central",
                "posture": "Charlie Coy high",
                "workload": "61h",
                "leave": "22 days",
                "incidents": "open window",
                "grievances": "land and property",
            },
            {
                "id": "north",
                "label": "North",
                "posture": "steady",
                "workload": "52h",
                "leave": "high",
                "incidents": "none",
                "grievances": "leave",
            },
            {
                "id": "east",
                "label": "East",
                "posture": "leave pressure",
                "workload": "55h",
                "leave": "backlog",
                "incidents": "none",
                "grievances": "family",
            },
            {
                "id": "capital",
                "label": "Capital",
                "posture": "steady",
                "workload": "49h",
                "leave": "held",
                "incidents": "none",
                "grievances": "few",
            },
        ],
        "sectors": [
            {"id": "C-02", "x": 42, "y": 48, "band": "T2"},
            {"id": "N-01", "x": 28, "y": 22, "band": "T0"},
            {"id": "E-02", "x": 70, "y": 40, "band": "T1"},
        ],
        "capacity": {
            "demand": "stretched",
            "recommend": "Move one counsellor day toward Central.",
        },
        "levers": {
            "note": "Observational, not causal",
            "items": [
                {"code": "REST_48H", "later_easing": "often", "n": "hidden"},
                {"code": "LEAVE_PRIORITISE", "later_easing": "often", "n": "hidden"},
            ],
        },
        "retention": {
            "transfer_requests": "banded",
            "exit_intent_tags": "suppressed under k",
        },
        "policy": {
            "leave_approval_rate": 0.62,
            "max_consecutive_duty": 10,
            "rotation_length_months": 24,
            "quick_return_cap": 2,
        },
        "brief": dict(HQ_BRIEF),
    }


def save_hq_brief(body: str) -> dict[str, Any]:
    HQ_BRIEF["body"] = body
    HQ_BRIEF["edited"] = True
    return dict(HQ_BRIEF)


def hq_simulate(policy: dict[str, Any]) -> dict[str, Any]:
    current = dict(hq_payload()["policy"])
    for key, value in policy.items():
        if key in current:
            current[key] = value
    return {
        "ok": True,
        "note": "Observational, not causal",
        "policy": current,
        "projected": (
            "Leave pressure eases if approval rate rises. "
            "Night load holds if the quick-return cap stays at two."
        ),
    }


def text_pdf(title: str, body: str) -> bytes:
    lines = [title, "Synthetic. Observational.", *body.splitlines()]
    content_lines = ["BT /F1 12 Tf 48 780 Td"]
    for line in lines[:40]:
        safe = (
            line.encode("ascii", "replace")
            .decode("ascii")
            .replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )
        content_lines.append(f"({safe[:110]}) Tj 0 -16 Td")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1")
    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        (
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        ),
        (
            b"4 0 obj << /Length "
            + str(len(stream)).encode("ascii")
            + b" >> stream\n"
            + stream
            + b"\nendstream endobj\n"
        ),
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(out))
        out.extend(obj)
    xref_at = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    out.extend(
        (
            f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_at}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(out)


def medical_referrals(scope_path: str) -> list[dict[str, str]]:
    del scope_path
    return [
        {
            "from": "UWO",
            "case_id": "MB-6604",
            "context": "Acute path. Minimum necessary. No journal.",
        }
    ]


def acute_guide() -> dict[str, Any]:
    return {
        "title": "Stay with the person",
        "steps": [
            "Stay with the person.",
            "Reach them in person if you can.",
            "Involve the medical officer.",
            "Follow force policy on the environment around them.",
        ],
        "note": "This is a human-administered guide. The system never scores people this way.",
    }


def counsel_desk(language: str = "hi") -> dict[str, Any]:
    requests = []
    for req in COUNSEL_REQUESTS:
        match = match_counsellor(str(req["language"]))
        requests.append({**req, "routed_to": match["counsellor"]})
    from .calls import acs_configured

    acs = acs_configured()
    return {
        "calendar": ["09:30 named Hindi", "11:00 anonymous English", "16:00 free"],
        "requests": requests,
        "routing": match_counsellor(language),
        "acs": {
            "demo_join": not acs,
            "label": "Join call" if acs else "Demo join. Azure Communication Services is unset.",
        },
        "notes_scope": "counsellor",
    }


def save_counsel_note(session_id: str, note: str) -> dict[str, str]:
    COUNSEL_NOTES[session_id] = note
    return {"session_id": session_id, "scope": "counsellor", "stored": "private"}


def suggest_lever(case_id: str, code: str, sentence: str) -> dict[str, str]:
    row = {
        "case_id": case_id,
        "lever": code,
        "summary": sentence[:180],
    }
    COUNSEL_SUGGESTIONS.append(row)
    return {**row, "notes_shared": False}

