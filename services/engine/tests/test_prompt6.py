from __future__ import annotations

from app.main import app
from app.personalisation import PERSONALISATION_FIELDS
from app.personnel import FORBIDDEN_OFFICER, SCORING_FIELDS, CheckInBody, scoring_payload
from app.recommender import rank_toolkit
from app.scoring.forecast import ADVERSE_FEATURES, EXCLUDED_ATTRIBUTES
from fastapi.testclient import TestClient

client = TestClient(app)


def _auth(role: str, persona_id: str | None = None) -> dict[str, str]:
    body: dict[str, str] = {"role": role}
    if persona_id:
        body["persona_id"] = persona_id
    token = client.post("/api/v1/auth/demo-login", json=body).json()["access_token"]
    return {"authorization": f"Bearer {token}"}


def test_onboarding_completes_for_arjun() -> None:
    headers = _auth("personnel", "arjun")
    start = client.get("/api/v1/me/onboarding", headers=headers)
    assert start.status_code == 200, start.text
    assert start.json()["consents"][0]["id"] == "hr_derived"
    done = client.post(
        "/api/v1/me/onboarding",
        headers=headers,
        json={
            "language": "hi",
            "consents": {"hr_derived": True, "self_report": True},
            "exception_understood": True,
            "simple_mode": True,
            "helpers": ["music", "talking to someone"],
            "family_context": "partner_and_child",
            "skip_buddy": True,
            "skip_safety_plan": True,
            "skip_wearable": True,
            "device_tier": "B",
        },
    )
    assert done.status_code == 200, done.text
    receipt = done.json()["receipt"]
    assert len(receipt["hash"]) == 64
    assert receipt["skipped"]["buddy"] is True
    home = client.get("/api/v1/me/home", headers=headers)
    assert home.status_code == 200
    assert home.json()["onboarding_done"] is True
    assert home.json()["greeting"] == "Suprabhat, Arjun"


def test_onboarding_requires_exception() -> None:
    headers = _auth("personnel", "arjun")
    response = client.post(
        "/api/v1/me/onboarding",
        headers=headers,
        json={"exception_understood": False},
    )
    assert response.status_code == 422


def test_homes_differ_for_personas() -> None:
    arjun = client.get("/api/v1/me/home", headers=_auth("personnel", "arjun")).json()
    meena = client.get("/api/v1/me/home", headers=_auth("personnel", "meena")).json()
    karthik = client.get("/api/v1/me/home", headers=_auth("personnel", "karthik")).json()
    assert "Night duty" in arjun["shift_line"]
    assert "Leave window" in meena["shift_line"]
    assert "Settling" in karthik["shift_line"]
    assert arjun["greeting"] != meena["greeting"] != karthik["greeting"]
    assert "வணக்கம்" in karthik["greeting"]
    for payload in (arjun, meena, karthik):
        assert len(payload["context_cards"]) <= 2
        for card in payload["context_cards"]:
            assert card["why"]
    kinds = {card["kind"] for card in meena["context_cards"]}
    assert "leave" in kinds or "jitai" in kinds
    assert len(kinds) == len(meena["context_cards"])
    assert any(card["kind"] == "lifecycle" for card in karthik["context_cards"])


def test_checkin_busy_day_is_one_question() -> None:
    headers = _auth("personnel", "arjun")
    client.post("/api/v1/me/check-in", headers=headers, json={"skipped": True})
    client.post("/api/v1/me/check-in", headers=headers, json={"skipped": True})
    questions = client.get("/api/v1/me/check-in", headers=headers).json()
    assert questions["busy_day"] is True
    assert len(questions["questions"]) == 1
    assert questions["questions"][0]["id"] == "mood"
    saved = client.post(
        "/api/v1/me/check-in",
        headers=headers,
        json={"mood": 3, "channel": "tap", "tags": ["Duty"]},
    )
    assert saved.status_code == 200
    assert "Thank you" in saved.json()["message"] or "धन्यवाद" in saved.json()["message"]
    scoring = saved.json()["scoring"]
    assert set(scoring) <= SCORING_FIELDS
    for field in PERSONALISATION_FIELDS:
        assert field not in scoring


def test_toolkit_ranking_ignores_tier() -> None:
    order = rank_toolkit(
        {
            "time_of_day": "morning",
            "shift_phase": "post_duty",
            "theatre": "central",
            "lifecycle_state": "inducted",
            "helpers": ["music", "talking to someone"],
        }
    )
    assert order[0] in {"music_decompress", "sleep_wind_down", "tactical_nap", "post_duty"}
    assert "music_decompress" in order[:3] or "sleep_wind_down" in order[:3]
    try:
        rank_toolkit({"tier": "T3", "helpers": ["music"]})
        raise AssertionError("tier must be rejected")
    except ValueError:
        pass
    headers = _auth("personnel", "arjun")
    items = client.get("/api/v1/me/toolkit", headers=headers).json()["items"]
    assert items[0]["id"] in {"music_decompress", "sleep_wind_down", "tactical_nap", "post_duty"}


def test_phq9_item_nine_opens_safety() -> None:
    headers = _auth("personnel", "arjun")
    listed = client.get("/api/v1/me/assessments", headers=headers).json()["items"]
    audit = next(item for item in listed if item["id"] == "auditc")
    assert audit["self_only"] is True
    phq = client.post(
        "/api/v1/me/assessments/phq9",
        headers=headers,
        json={"item": 9, "value": 1, "conversational": True},
    )
    assert phq.json()["safety"] is True
    assert phq.json()["verbatim"] is True
    audit_save = client.post(
        "/api/v1/me/assessments/auditc",
        headers=headers,
        json={"item": 1, "value": 0},
    )
    assert audit_save.json()["device_only"] is True


def test_rest_meena_has_window() -> None:
    headers = _auth("personnel", "meena")
    rest = client.get("/api/v1/me/rest", headers=headers).json()
    assert rest["el_days"] >= 20
    assert rest["window"] is not None
    assert "does not submit leave" in rest["copy"]


def test_talk_acs_fallback_and_anonymous() -> None:
    headers = _auth("personnel", "arjun")
    named = client.post(
        "/api/v1/me/talk",
        headers=headers,
        json={"kind": "counsellor", "anonymous": False, "mode": "book"},
    )
    anon = client.post(
        "/api/v1/me/talk",
        headers=headers,
        json={"kind": "counsellor", "anonymous": True, "mode": "request"},
    )
    assert named.json()["demo_join"] is True
    assert "Demo join" in named.json()["demo_label"]
    assert anon.json()["request"]["handle"] == "River-17"


def test_buddy_payload_has_no_tier_or_token() -> None:
    headers = _auth("personnel", "arjun")
    paired = client.post("/api/v1/me/buddy", headers=headers, json={"action": "pair"})
    assert paired.json()["tier"] is None
    assert paired.json()["score"] is None
    assert paired.json().get("other_token") is None
    unpaired = client.post("/api/v1/me/buddy", headers=headers, json={"action": "unpair"})
    assert unpaired.json()["notified"] is False


def test_family_share_has_no_personal_data() -> None:
    headers = _auth("personnel", "meena")
    set_rem = client.post("/api/v1/me/family?reminder=sunday", headers=headers)
    assert set_rem.json()["personal_data"] is False
    public = client.get("/api/v1/family")
    assert public.json()["personal_data"] is False
    blob = str(public.json())
    assert "meena" not in blob.lower()
    assert "st_" not in blob


def test_rights_erase_receipt_and_remembers_default_off() -> None:
    headers = _auth("personnel", "arjun")
    remembers = client.get("/api/v1/me/remembers", headers=headers).json()
    assert remembers["opt_in"] is False
    erased = client.post("/api/v1/me/rights/erase?data_type=self_report", headers=headers)
    assert erased.status_code == 200
    assert erased.json()["sha256"]
    assert erased.json()["signature"]


def test_jitai_caps_and_not_now() -> None:
    headers = _auth("personnel", "arjun")
    home = client.get("/api/v1/me/home", headers=headers).json()
    jitai_cards = [card for card in home["context_cards"] if card["kind"] == "jitai"]
    assert len(jitai_cards) <= 1
    silenced = client.post("/api/v1/me/jitai/not-now", headers=headers).json()
    assert "silenced_until" in silenced
    later = client.get("/api/v1/me/home", headers=headers).json()
    assert all(card["kind"] != "jitai" for card in later["context_cards"])


def test_i18n_reviewed_and_tamil() -> None:
    hi = client.get("/api/v1/i18n/hi").json()
    assert hi["strings"]["safety.title"] == "आप अकेले नहीं हैं।"
    assert hi["reviewed"] is True
    ta = client.get("/api/v1/i18n/ta").json()
    assert "வணக்கம்" in ta["strings"]["home.greeting.karthik"]
    bn = client.get("/api/v1/i18n/bn").json()
    assert bn["machine_translated"] is True


def test_personalisation_never_in_scoring_or_officer_payloads() -> None:
    for field in PERSONALISATION_FIELDS:
        assert field not in ADVERSE_FEATURES
    assert "language" in EXCLUDED_ATTRIBUTES
    body = CheckInBody(mood=2, energy=3, sleep_quality=2, tags=["Duty"])
    payload = scoring_payload("st_example", body)
    for field in PERSONALISATION_FIELDS:
        assert field not in payload
    welfare = client.get("/api/v1/welfare/queue", headers=_auth("uwo")).json()
    command = client.get("/api/v1/command/posture", headers=_auth("commander")).json()
    blob = (str(welfare) + str(command)).lower()
    for field in FORBIDDEN_OFFICER:
        assert field not in blob


def test_jitai_skips_during_duty() -> None:
    from app.personnel import evaluate_jitai

    assert (
        evaluate_jitai(
            {
                "on_duty": True,
                "night_within_24h": True,
                "jitai_day_count": 0,
                "jitai_week_count": 0,
            },
            "arjun",
        )
        is None
    )


def test_edge_link_holds_packets() -> None:
    director = _auth("director")
    down = client.post("/api/v1/demo/edge-link", headers=director, json={"up": False})
    assert down.json()["up"] is False
    headers = _auth("personnel", "arjun")
    held = client.post(
        "/api/v1/me/sync",
        headers=headers,
        json=[{"kind": "checkin", "client_id": "c1", "payload": {"mood": 3}}],
    )
    assert held.json()["edge_up"] is False
    assert held.json()["held"] == 1
    up = client.post("/api/v1/demo/edge-link", headers=director, json={"up": True})
    assert up.json()["up"] is True
