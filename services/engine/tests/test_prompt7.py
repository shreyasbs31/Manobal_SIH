from __future__ import annotations

from app.main import app
from app.officers import chime_kind_for_queue, copilot_answer, text_pdf
from fastapi.testclient import TestClient

client = TestClient(app)


def _auth(role: str, persona_id: str | None = None) -> dict[str, str]:
    body: dict[str, str] = {"role": role}
    if persona_id:
        body["persona_id"] = persona_id
    token = client.post("/api/v1/auth/demo-login", json=body).json()["access_token"]
    return {"authorization": f"Bearer {token}"}


def test_welfare_queue_lists_arjun_under_high() -> None:
    headers = _auth("uwo")
    queue = client.get("/api/v1/welfare/queue", headers=headers)
    assert queue.status_code == 200, queue.text
    items = queue.json()
    arjun = next(item for item in items if item["case_id"] == "MB-4091")
    assert arjun["tier"] == "T3"
    tabs = client.get("/api/v1/welfare/tabs", headers=headers).json()
    assert "MB-4091" in tabs["t3"]
    assert tabs["followups"]
    assert tabs["self_referrals"]
    assert tabs["workload"]


def test_reveal_writes_ledger_for_arjun() -> None:
    uwo = _auth("uwo")
    arjun = _auth("personnel", "arjun")
    before = client.get("/api/v1/me/access-ledger", headers=arjun).json()["items"]
    denied = client.post(
        "/api/v1/welfare/cases/MB-4091/reveal",
        headers=uwo,
        json={"purpose_code": "care_contact", "justification": "short"},
    )
    assert denied.status_code == 422
    revealed = client.post(
        "/api/v1/welfare/cases/MB-4091/reveal",
        headers=uwo,
        json={
            "purpose_code": "care_contact",
            "justification": "Need to call about rest after duty.",
        },
    )
    assert revealed.status_code == 200, revealed.text
    body = revealed.json()
    assert body["revealed"] is True
    assert body["card"]["synthetic"] is True
    assert "viewed their identity" in body["notice"]
    note = client.post(
        "/api/v1/welfare/contact-note",
        headers=uwo,
        json={"grant_id": body["grant_id"], "note": "Called the unit welfare line."},
    )
    assert note.status_code == 200
    action = client.post(
        "/api/v1/welfare/cases/MB-4091/action",
        headers=uwo,
        json={
            "mode": "call",
            "lever": "REST_48H",
            "outcome": "open",
            "follow_up": "D+2",
            "refer": "",
        },
    )
    assert action.status_code == 200
    ledger = client.get("/api/v1/me/access-ledger", headers=arjun).json()["items"]
    assert len(ledger) > len(before)
    assert any(row.get("action") == "identity.viewed" for row in ledger)
    case = client.get("/api/v1/welfare/cases/MB-4091", headers=uwo).json()
    assert "token" not in case
    assert "[tier]" in case["brief"]
    assert case["brief_fields"]["lever"] == "REST_48H"
    assert any(lever["code"] == "NO_ACTION" for lever in case["levers"])


def test_counsellor_desk_routes_hindi_and_keeps_notes_private() -> None:
    headers = _auth("counsellor")
    desk = client.get("/api/v1/counsel/desk", headers=headers, params={"language": "hi"})
    assert desk.status_code == 200, desk.text
    payload = desk.json()
    assert payload["routing"]["counsellor"] == "counsellor-anjali"
    hindi = next(item for item in payload["requests"] if item["language"] == "hi")
    assert hindi["routed_to"] == "counsellor-anjali"
    assert payload["acs"]["demo_join"] is True
    notes = client.post(
        "/api/v1/counsel/notes",
        headers=headers,
        json={"session_id": "req-hi-1", "note": "Private counsellor note"},
    )
    assert notes.status_code == 200
    assert notes.json()["scope"] == "counsellor"
    suggest = client.post(
        "/api/v1/counsel/suggest",
        headers=headers,
        json={"case_id": "MB-4091", "lever": "REST_48H", "sentence": "A rest cycle may help."},
    )
    assert suggest.status_code == 200
    assert suggest.json()["lever"] == "REST_48H"
    assert suggest.json()["notes_shared"] is False
    welfare = client.get("/api/v1/welfare/queue", headers=headers)
    assert welfare.status_code == 403


def test_medical_acute_board_and_guide() -> None:
    headers = _auth("mo")
    board = client.get("/api/v1/medical/acute", headers=headers)
    assert board.status_code == 200, board.text
    items = board.json()
    deepak = next(item for item in items if item["case_id"] == "MB-6604")
    assert deepak["tier"] == "T4"
    ack = client.post("/api/v1/medical/acute/MB-6604/ack", headers=headers)
    assert ack.status_code == 200
    assert ack.json()["status"] == "ack"
    referrals = client.get("/api/v1/medical/referrals", headers=headers).json()
    assert referrals["items"][0]["case_id"] == "MB-6604"
    assert "journal" in referrals["items"][0]["context"].lower() or "minimum" in referrals["items"][0]["context"].lower()
    note = referrals["guide"]["note"].lower()
    assert "suicide risk score" not in note
    assert "self-harm" in note or "never scores" in note


def test_command_hides_post_d7_and_refuses_individual_copilot() -> None:
    headers = _auth("commander")
    posture = client.get("/api/v1/command/posture", headers=headers)
    assert posture.status_code == 200, posture.text
    body = posture.json()
    assert "Post D-7" in body["companies"]
    hidden = [cell for cell in body["cells"] if cell["unit"] == "Post D-7"]
    assert hidden
    assert all(cell["band"] == "hidden" for cell in hidden)
    assert "MB-4091" not in posture.text
    roster = client.get("/api/v1/command/roster", headers=headers).json()
    locked = next(row for row in roster["companies"] if row["label"] == "Post D-7")
    assert locked["locked"] is True
    denied = client.post("/api/v1/command/simulate", headers=headers, json={"n": 7})
    assert denied.status_code == 422
    projected = client.post(
        "/api/v1/command/simulate",
        headers=headers,
        json={"companies": roster["companies"]},
    )
    assert projected.status_code == 200
    assert projected.json()["locked"]
    question = "Charlie Coy mein kaun pareshan hai?"
    copilot = client.post(
        "/api/v1/command/copilot",
        headers=headers,
        json={"question": question, "lang": "hi"},
    )
    assert copilot.status_code == 200, copilot.text
    answer = copilot.json()
    assert answer["refuse"] is True
    assert "20" in answer["answer"] and "30" in answer["answer"]
    assert "Charlie Coy" in answer["answer"]
    local = copilot_answer(question, "hi")
    assert local["refuse"] is True


def test_individual_copilot_never_imports_gateway(monkeypatch) -> None:
    headers = _auth("commander")

    def boom(*_args, **_kwargs):
        raise AssertionError("model must not run for individual questions")

    monkeypatch.setattr("app.ai.gateway.run", boom)
    copilot = client.post(
        "/api/v1/command/copilot",
        headers=headers,
        json={"question": "Charlie Coy mein kaun pareshan hai?", "lang": "hi"},
    )
    assert copilot.status_code == 200
    assert copilot.json()["refuse"] is True
    assert copilot.json()["provider"] == "refused"


def test_aggregate_hindi_question_is_not_individual() -> None:
    from app.officers import INDIVIDUAL_RE

    question = "चार्ली कॉय की ड्यूटी तीन सप्ताह से ऊपर है। क्या रात की पाली घटाई जा सकती है?"
    assert INDIVIDUAL_RE.search(question) is None
    headers = _auth("commander")
    copilot = client.post(
        "/api/v1/command/copilot",
        headers=headers,
        json={"question": question, "lang": "hi"},
    )
    assert copilot.status_code == 200, copilot.text
    assert copilot.json()["refuse"] is False


def test_hq_brief_edits_and_exports_pdf() -> None:
    headers = _auth("hq")
    overview = client.get("/api/v1/hq/overview", headers=headers)
    assert overview.status_code == 200, overview.text
    payload = overview.json()
    assert payload["levers"]["note"] == "Observational, not causal"
    saved = client.post(
        "/api/v1/hq/brief",
        headers=headers,
        json={"body": "Leave backlog is high in the north theatre [leave_backlog]."},
    )
    assert saved.status_code == 200
    assert saved.json()["edited"] is True
    pdf = client.get("/api/v1/hq/brief.pdf", headers=headers)
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")
    assert text_pdf("Title", "Body").startswith(b"%PDF-1.4")
    sim = client.post(
        "/api/v1/hq/simulate",
        headers=headers,
        json={"leave_approval_rate": 0.8, "rotation_length_months": 18},
    )
    assert sim.status_code == 200
    assert sim.json()["policy"]["leave_approval_rate"] == 0.8


def test_officer_personas_match_spec() -> None:
    sunita = client.get("/api/v1/officer/profile", headers=_auth("uwo")).json()
    assert sunita["brief_language"] == "hi"
    assert sunita["digest_time"] == "08:00"
    assert sunita["opener_tone"] == "informal"
    anjali = client.get("/api/v1/officer/profile", headers=_auth("counsellor")).json()
    assert set(anjali["languages"]) >= {"hi", "mr", "en"}
    menon = client.get("/api/v1/officer/profile", headers=_auth("commander")).json()
    assert menon["copilot_language"] == "hi"
    farah = client.get("/api/v1/officer/profile", headers=_auth("mo")).json()
    assert "Mon" in farah["on_call"]
    hq = client.get("/api/v1/officer/profile", headers=_auth("hq")).json()
    assert hq["policy_lens"] == "rotation_length"
    kavita = client.get("/api/v1/officer/profile", headers=_auth("wdec")).json()
    assert "gate_hit_rates" in kavita["watchlists"]


def test_console_chime_kind() -> None:
    assert chime_kind_for_queue(1, 2) == "t4"
    assert chime_kind_for_queue(0, 1) == "t3"
    assert chime_kind_for_queue(0, 0) == ""
