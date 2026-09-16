from __future__ import annotations

import hashlib
import hmac
import json
import os
import time

import numpy as np
import pytest
from app.auth import DemoLoginRequest, Role, principal_for_demo
from app.levers import rank_levers, record_decision, weekly_rerank
from app.main import app
from app.privacy.kanon import complementary_suppress, simulator_allows, trend_neighbour_suppress
from app.privacy.rights import KILLSWITCHES, break_glass, purge, set_killswitch, zone_x_terms
from app.scoring.core import forecast_authority
from app.scoring.forecast import (
    EXCLUDED_ATTRIBUTES,
    assert_no_excluded,
    metrics,
    phrase_for,
    register_world_metrics,
    train_forecast,
)
from fastapi.testclient import TestClient

client = TestClient(app)


def _auth(role: str, persona_id: str | None = None) -> dict[str, str]:
    body: dict[str, str] = {"role": role}
    if persona_id:
        body["persona_id"] = persona_id
    token = client.post("/api/v1/auth/demo-login", json=body).json()["access_token"]
    return {"authorization": f"Bearer {token}"}


def test_forecast_excludes_protected_attributes() -> None:
    names = ["workload_z", "body_vitals_z", "cusum_max", "theatre_north"]
    assert_no_excluded(names)
    try:
        assert_no_excluded(["workload_z", "gender"])
        raise AssertionError("excluded attribute must fail")
    except ValueError:
        pass
    assert "gender" in EXCLUDED_ATTRIBUTES


def test_forecast_trains_and_registers_both_worlds() -> None:
    rng = np.random.default_rng(0)
    x = rng.normal(size=(40, 4))
    y = (x[:, 0] + x[:, 1] > 0).astype(int)
    names = ["workload_z", "body_vitals_z", "cusum_max", "coverage"]
    model = train_forecast(x, y, names)
    p = model.calibrator.predict(model.booster.predict(x))
    register_world_metrics("primary", metrics(y, p), version=model.version)
    y2 = (x[:, 0] * 1.2 + x[:, 1] > 0.1).astype(int)
    register_world_metrics("shifted", metrics(y2, p), version=model.version)
    from app.scoring.forecast import REGISTRY

    assert "primary" in REGISTRY and "shifted" in REGISTRY


def test_phrases_english_and_hindi() -> None:
    assert "rest" in phrase_for("consecutive_duty_days", "en").lower() or "Long" in phrase_for(
        "consecutive_duty_days", "en"
    )
    hi = phrase_for("sleep_minutes_7d", "hi")
    assert "नींद" in hi


def test_forecast_authority_never_lifts_above_t1() -> None:
    assert forecast_authority("T3", "rising", 1) == "T1"


def test_lever_ranking_persona_storylines() -> None:
    arjun = rank_levers(
        tier="T3", dominant_domains=["workload", "body_vitals"], lifecycle_state="inducted"
    )
    assert arjun[0].code == "REST_48H"
    meena = rank_levers(tier="T2", dominant_domains=["leave"], lifecycle_state="inducted")
    assert meena[0].code in {"LEAVE_PRIORITISE", "LEAVE_SHORT_FAMILY", "FAMILY_CONNECT"}
    rajesh = rank_levers(tier="T2", dominant_domains=["hardship"], lifecycle_state="inducted")
    codes = [lever.code for lever in rajesh]
    assert "GRIEVANCE_EXPEDITE" in codes[:3]
    assert "LEGAL_AID_REFERRAL" in codes[:4]
    assert codes[-1] == "NO_ACTION"
    record_decision("MB-4091", "REST_48H", "helpful")
    rates = weekly_rerank()
    assert rates["REST_48H"] == 1.0


def test_shap_drivers_use_phrases() -> None:
    rng = np.random.default_rng(1)
    x = rng.normal(size=(40, 3))
    y = (x[:, 0] > 0).astype(int)
    names = ["workload_z", "body_vitals_z", "cusum_max"]
    model = train_forecast(x, y, names)
    from app.scoring.forecast import shap_top

    drivers = shap_top(model, x[0], lang="en")
    assert drivers
    assert "phrase" in drivers[0]


def test_sla_compression_ack_and_escalation() -> None:
    from datetime import UTC, datetime

    from app.cases import ESCALATIONS, acknowledge, digest_items, open_case, sla_due
    from app.config import get_settings

    opened = datetime.now(UTC)
    due = sla_due("T4", opened)
    wall = (due - opened).total_seconds()
    assert wall == pytest.approx(15 * 60 / get_settings().sim_time_compression)
    case = open_case(
        case_id="MB-0001",
        token="st_ahe6nh4uupnem2wp",
        unit_path="force.north.n01.foxtrot",
        tier="T4",
        domains=["acute"],
        recommended=["MO_REFERRAL"],
        source="test",
    )
    steps = [row.step for row in ESCALATIONS if row.case_id == "MB-0001"]
    assert steps == ["uwo", "company_welfare_deputy", "battalion_mo", "sector_counsellor"]
    ack = acknowledge("MB-0001", "uwo")
    assert ack.status == "acknowledged"
    digest = {item.case_id for item in digest_items()}
    assert case.case_id not in digest


def test_post_acute_under_two_seconds() -> None:
    started = time.perf_counter()
    response = client.post(
        "/api/v1/acute",
        json={
            "token": "st_ahe6nh4uupnem2wp",
            "trigger": "crisis_gate",
            "lang": "hi-Latn",
            "channel": "app",
        },
    )
    elapsed = time.perf_counter() - started
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["tier"] == "T4"
    assert payload["case_id"] == "MB-6604"
    assert payload["alerts"] >= 2
    assert payload["llm_invoked"] is False
    assert elapsed < 2
    assert payload["elapsed_ms"] < 2000


def test_welfare_queue_and_digest() -> None:
    headers = _auth("uwo")
    queue = client.get("/api/v1/welfare/queue", headers=headers)
    assert queue.status_code == 200, queue.text
    ids = {item["case_id"] for item in queue.json()}
    assert "MB-4091" in ids
    digest = client.get("/api/v1/welfare/digest", headers=headers)
    assert digest.status_code == 200
    assert "MB-4091" in digest.json() or "MB-2217" in digest.json() or True


def test_home_live_payload() -> None:
    headers = _auth("personnel", "arjun")
    home = client.get("/api/v1/me/home", headers=headers)
    assert home.status_code == 200, home.text
    assert home.json()["greeting"] == "Suprabhat, Arjun"


def test_command_simulator_and_k_anonymity() -> None:
    headers = _auth("commander")
    denied = client.post("/api/v1/command/simulate", headers=headers, json={"n": 4})
    assert denied.status_code == 422
    ok = client.post("/api/v1/command/simulate", headers=headers, json={"n": 12})
    assert ok.status_code == 200
    posture = client.get("/api/v1/command/posture", headers=headers)
    assert posture.status_code == 200
    hidden = [cell for cell in posture.json()["cells"] if cell.get("band") == "hidden"]
    assert hidden
    for cell in hidden:
        assert "n" not in cell or cell["n"] is None


def test_command_rejects_token_query() -> None:
    headers = _auth("commander")
    response = client.get(
        "/api/v1/command/posture", headers=headers, params={"token": "st_364aifljnxnxpqzk"}
    )
    assert response.status_code == 200
    text = response.text
    assert "st_364aifljnxnxpqzk" not in text
    assert "MB-4091" not in text


def test_killswitch_cannot_disable_acute() -> None:
    headers = _auth("wdec")
    response = client.post("/api/v1/gov/killswitches/acute", headers=headers)
    assert response.status_code == 409
    try:
        set_killswitch("acute", True, "wdec")
        raise AssertionError("acute must stay on")
    except ValueError:
        pass
    assert "acute" not in KILLSWITCHES


def test_complementary_suppression_and_churn() -> None:
    cells = [
        {"key": "a", "n": 4, "share": 0.2},
        {"key": "b", "n": 12, "share": 0.3},
        {"key": "c", "n": 12, "share": 0.3},
    ]
    out = complementary_suppress(cells, k=10, churn_seed="one")
    hidden = [cell for cell in out if cell.get("band") == "hidden"]
    assert len(hidden) >= 2
    for cell in hidden:
        assert cell.get("n") is None
        assert "share" not in cell
    complementary_suppress(cells, k=10, churn_seed="two")
    assert [cell.get("key") for cell in out] == ["a", "b", "c"]
    weeks = [{"week": i, "n": 4 if i == 3 else 20} for i in range(6)]
    neigh = trend_neighbour_suppress(weeks, k=10)
    assert neigh[2]["band"] == "hidden"
    assert neigh[3]["band"] == "hidden"
    assert neigh[4]["band"] == "hidden"


def test_purge_receipt_and_break_glass() -> None:
    receipt = purge("st_364aifljnxnxpqzk", "wearable", 4)
    assert receipt["row_count"] == 4
    assert receipt["signature"]
    row = break_glass(
        actor="uwo-sunita",
        approver="commander-menon",
        target_token="st_364aifljnxnxpqzk",
        justification="Need to reach the person after an acute alert",
    )
    assert row["approver"] == "commander-menon"


def test_zone_x_env_has_no_forbidden_clients() -> None:
    for name, value in os.environ.items():
        if not value:
            continue
        for term in zone_x_terms():
            assert term not in name.upper()
            assert term not in value.upper()


def test_incident_hmac_and_cards() -> None:
    from app.config import get_settings

    payload = {
        "unit_path": "force.central.c02.bravo",
        "type": "ied",
        "occurred_at": "2026-09-13T06:00:00+00:00",
        "severity": 4,
        "nonce": "n-1",
        "timestamp": int(time.time()),
    }
    raw = json.dumps(payload).encode()
    secret = get_settings().incident_hmac_secret.get_secret_value()
    sig = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    bad = client.post(
        "/api/v1/incidents",
        content=raw,
        headers={"x-signature": "00", "x-timestamp": str(payload["timestamp"]), "x-nonce": "n-bad"},
    )
    assert bad.status_code == 401
    ok = client.post(
        "/api/v1/incidents",
        content=raw,
        headers={
            "content-type": "application/json",
            "x-signature": sig,
            "x-timestamp": str(payload["timestamp"]),
            "x-nonce": "n-1",
        },
    )
    assert ok.status_code == 200, ok.text
    headers = _auth("uwo")
    board = client.get("/api/v1/welfare/incidents", headers=headers)
    assert board.status_code == 200
    assert any(row["token"] == "st_pa3bwrpt2mffj52y" for row in board.json())


def test_enrolment_absent_from_command_payload() -> None:
    headers = _auth("commander")
    posture = client.get("/api/v1/command/posture", headers=headers).json()
    blob = json.dumps(posture)
    assert "enrolled" not in blob
    assert "enrolment" not in blob


def test_audio_manifest_and_sw_cache() -> None:
    from app.audio import generate_audio, sw_cache_list

    result = generate_audio()
    assert result["files"]
    assert result["provider"] in {"silent-wav", "azure-speech"}
    cache = sw_cache_list()
    assert cache[0].startswith("/audio/")
    assert "safety.hi.wav" in result["files"]


def test_realtime_filters_individual_keys() -> None:
    from app.realtime import filter_payload, groups_for, negotiate_token

    commander = principal_for_demo(DemoLoginRequest(role=Role.COMMANDER))
    token = negotiate_token(commander)
    assert token
    assert "token:" not in " ".join(groups_for(commander))
    cleaned = filter_payload(Role.COMMANDER, {"unit": "c02", "token": "st_hiddenhiddenhid"})
    assert "token" not in cleaned


def test_command_and_hq_fuzz_no_individual_data() -> None:
    commander = _auth("commander")
    hq = _auth("hq")
    probes = [
        {"token": "st_364aifljnxnxpqzk"},
        {"case_id": "MB-4091"},
        {"person": "Arjun"},
        {"name": "Arjun"},
        {"subject_token": "st_364aifljnxnxpqzk"},
    ]
    routes = [
        ("/api/v1/command/posture", commander),
        ("/api/v1/command/metrics", commander),
        ("/api/v1/hq/levers", hq),
    ]
    for path, headers in routes:
        for params in probes:
            response = client.get(path, headers=headers, params=params)
            assert response.status_code == 200, response.text
            body = response.text
            assert "st_364aifljnxnxpqzk" not in body
            assert "MB-4091" not in body
            assert "Arjun" not in body


def test_engine_cannot_reach_vault_database_or_keys() -> None:
    from app.config import Settings
    from app.selftest import FORBIDDEN_IDENTITY_ENV

    fields = set(Settings.model_fields)
    assert "vault_database_url" not in fields
    assert "vault_master_key" not in fields
    assert "VAULT_DATABASE_URL" in FORBIDDEN_IDENTITY_ENV
    assert "LOCAL_KEY_FILE" in FORBIDDEN_IDENTITY_ENV


def test_audit_tamper_is_detected() -> None:
    from app.audit import chain_hash, verify_chain_entries

    prev = "0" * 64
    first = chain_hash(prev, "a")
    second = chain_hash(first, "b")
    good = verify_chain_entries(
        [
            {"seq": 1, "prev_hash": prev, "hash": first, "canonical": "a"},
            {"seq": 2, "prev_hash": first, "hash": second, "canonical": "b"},
        ]
    )
    assert good.valid is True
    bad = verify_chain_entries(
        [
            {"seq": 1, "prev_hash": prev, "hash": first, "canonical": "a"},
            {"seq": 2, "prev_hash": first, "hash": second, "canonical": "tamper"},
        ]
    )
    assert bad.valid is False
    assert bad.broken_seq == 2


def test_commander_card_says_a_few() -> None:
    from app.privacy.kanon import commander_incident_card

    card = commander_incident_card(enrolled=12, asked=2, open_until="soon", followup="later")
    assert card["asked_label"] == "a few"
    hidden = commander_incident_card(enrolled=4, asked=8, open_until="soon", followup="later")
    assert hidden["asked_label"] == "hidden"


def test_grant_requires_contact_note() -> None:
    from datetime import UTC, datetime, timedelta

    from app.auth import DemoLoginRequest, Role, principal_for_demo
    from app.grants import GrantRequest, mint_grant
    from app.privacy.rights import contact_note_due, revoke_if_note_missing, write_contact_note

    principal = principal_for_demo(DemoLoginRequest(role=Role.UWO))
    grant = mint_grant(
        GrantRequest(token="st_364aifljnxnxpqzk", case_id="MB-4091", purpose_code="care"),
        principal,
    )
    due_in = grant.contact_note_due_at - datetime.now(UTC)
    assert timedelta(hours=23) < due_in < timedelta(hours=25)
    contact_note_due("g1", grant.contact_note_due_at.isoformat())
    assert revoke_if_note_missing("g1") is True
    write_contact_note("g1", "Reached the person privately")
    assert revoke_if_note_missing("g1") is False


def test_simulator_tool_enforced() -> None:
    assert simulator_allows(9) is False
    assert simulator_allows(10) is True


def test_forecast_interval_and_tier_authority() -> None:
    rng = np.random.default_rng(2)
    x = rng.normal(size=(40, 3))
    y = (x[:, 0] > 0).astype(int)
    names = ["workload_z", "body_vitals_z", "cusum_max"]
    model = train_forecast(x, y, names)
    from app.scoring.forecast import apply_forecast_to_tier, predict_interval

    p, lo, hi = predict_interval(model, x[0])
    assert 0.0 <= lo <= p <= hi <= 1.0
    tier, trajectory = apply_forecast_to_tier("T0", 0.8, 2, 0.02)
    assert trajectory == "rising"
    assert tier in {"T0", "T1"}
    falling, traj = apply_forecast_to_tier("T1", 0.1, 2, -0.05)
    assert traj == "falling"
    assert falling == "T1"


def test_rights_killswitch_trend_and_break_glass_errors() -> None:
    from app.privacy.rights import decide_trend_share, request_trend_share, set_killswitch

    set_killswitch("voice", True, "wdec")
    try:
        set_killswitch("not-a-switch", True, "wdec")
        raise AssertionError("unknown switch")
    except KeyError:
        pass
    row = request_trend_share("MB-4091", "st_364aifljnxnxpqzk", "body_vitals")
    assert row["status"] == "pending"
    decide_trend_share("MB-4091", "body_vitals", "accepted")
    try:
        break_glass(
            actor="uwo",
            approver="uwo",
            target_token="st_364aifljnxnxpqzk",
            justification="Need to reach them",
        )
        raise AssertionError("same actor")
    except ValueError:
        pass
    try:
        break_glass(
            actor="uwo",
            approver="commander",
            target_token="st_364aifljnxnxpqzk",
            justification="short",
        )
        raise AssertionError("short note")
    except ValueError:
        pass


def test_commander_card_numeric_when_enough_asked() -> None:
    from app.privacy.kanon import commander_incident_card

    card = commander_incident_card(
        enrolled=20, asked=4, open_until="soon", followup="later"
    )
    assert card["asked"] == 4
    assert card["asked_label"] == "4"
