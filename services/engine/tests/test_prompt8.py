from __future__ import annotations

from app.main import app
from app.scoring.forecast import EXCLUDED_ATTRIBUTES
from fastapi.testclient import TestClient

client = TestClient(app)


def _auth(role: str, persona_id: str | None = None) -> dict[str, str]:
    body: dict[str, str] = {"role": role}
    if persona_id:
        body["persona_id"] = persona_id
    token = client.post("/api/v1/auth/demo-login", json=body).json()["access_token"]
    return {"authorization": f"Bearer {token}"}


def test_governance_kpis_parity_ruleset_and_locked_acute() -> None:
    headers = _auth("wdec")
    kpis = client.get("/api/v1/gov/kpis", headers=headers)
    assert kpis.status_code == 200, kpis.text
    labels = {row["label"] for row in kpis.json()["kpis"]}
    assert "Lead time" in labels
    assert "False-positive rate" in labels
    assert "Enrolment integrity" in labels
    fairness = client.get("/api/v1/gov/fairness", headers=headers).json()
    assert fairness["band"] == "0.80 to 1.25"
    assert all(row["within_band"] for row in fairness["exposure_parity"])
    rules = client.get("/api/v1/gov/rulesets", headers=headers).json()
    assert rules["signed"] is True
    assert rules["signers"] == ["wdec1", "wdec2"]
    models = client.get("/api/v1/gov/models", headers=headers).json()
    assert models["card"]["trained_on"].startswith("primary")
    assert "gender" in models["card"]["excluded"]
    locked = client.post("/api/v1/gov/killswitches/acute", headers=headers)
    assert locked.status_code == 409
    report = client.post("/api/v1/gov/transparency-report", headers=headers)
    assert report.status_code == 200
    pdf = client.get("/api/v1/gov/transparency-report.pdf", headers=headers)
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"


def test_audit_tamper_then_restore() -> None:
    headers = _auth("wdec")
    intact = client.get("/api/v1/gov/audit", headers=headers).json()
    assert intact["valid"] is True
    client.post("/api/v1/gov/audit/tamper", headers=headers)
    broken = client.post("/api/v1/gov/audit/verify", headers=headers).json()
    assert broken["valid"] is False
    client.post("/api/v1/gov/audit/restore", headers=headers)
    healed = client.get("/api/v1/gov/audit", headers=headers).json()
    assert healed["valid"] is True
    assert healed["mode"] == "heal"


def test_dpo_trust_integrations_admin() -> None:
    dpo = _auth("dpo")
    requests = client.get("/api/v1/dpo/requests", headers=dpo).json()
    kinds = {row["kind"] for row in requests["requests"]}
    assert {"access", "erasure", "grievance"} <= kinds
    closed = client.post(
        f"/api/v1/dpo/requests/{requests['requests'][0]['id']}",
        headers=dpo,
        json={"decision": "closed"},
    )
    assert closed.status_code == 200
    trust = client.get("/api/v1/public/trust").json()
    assert len(trust["matrix"]) == 4
    assert "Support, not surveillance" in trust["promise"]
    assert trust["read_aloud"]
    integrator = _auth("hrms_integrator")
    jobs = client.get("/api/v1/integrations/jobs", headers=integrator).json()
    assert jobs["quarantine"]
    assert "name" in jobs["contracts"][0]["forbidden"]
    probe = client.post(
        "/api/v1/integrations/hrms/upload",
        headers=integrator,
        json={"filename": "probe.csv", "rows": [{"full_name": "blocked"}]},
    )
    assert probe.json()["held"] == 1
    admin = _auth("admin")
    console = client.get("/api/v1/admin/console", headers=admin).json()
    assert console["acute_listed"] is False
    banned = client.post(
        "/api/v1/admin/flags",
        headers=admin,
        json={"name": "acute", "enabled": False},
    )
    assert banned.status_code == 409


def test_lab_worlds_zero_penalty_and_benchmark() -> None:
    headers = _auth("wdec")
    primary = client.get("/api/v1/lab/metrics?world=primary", headers=headers).json()
    shifted = client.get("/api/v1/lab/metrics?world=shifted", headers=headers).json()
    assert primary["world"] == "primary"
    assert shifted["world"] == "shifted"
    assert "Imran stays T1" in primary["personas"]["imran"]
    assert "Thomas stays T0" in primary["personas"]["thomas"]
    assert primary["zero_penalty"]["present_in_model"] is False
    assert EXCLUDED_ATTRIBUTES.issubset(set(primary["zero_penalty"]["excluded"]))
    bench = client.post("/api/v1/lab/benchmark", headers=headers).json()
    assert bench["subjects"] == 8000


def test_architecture_edge_and_mode() -> None:
    director = _auth("director")
    live = client.get("/api/v1/public/architecture").json()
    assert "mode" in live
    down = client.post("/api/v1/demo/edge-link", headers=director, json={"up": False})
    assert down.status_code == 200
    held = client.get("/api/v1/public/architecture").json()
    assert held["edge_up"] is False
    client.post("/api/v1/demo/edge-link", headers=director, json={"up": True})
    mode = client.get("/api/v1/system/mode").json()
    assert mode["mode"] in {"demo", "sovereign"}
    selftest = client.get("/api/v1/system/selftest").json()
    assert "vault_database_isolated" in selftest
    assert "zone_x_unreachable" in selftest


def test_director_scenarios_reset_and_outage() -> None:
    headers = _auth("director")
    board = client.get("/api/v1/director/board", headers=headers).json()
    ids = {row["id"] for row in board["scenarios"]}
    assert {
        "arjun_drift",
        "deepak_acute",
        "lalit_incident",
        "meena_leave",
        "karthik_return",
        "rajesh_grievance",
    } <= ids
    shot_ids = {row["id"] for row in board["shots"]}
    assert {"landing", "workspace", "deepak", "governance", "lab", "architecture"} <= shot_ids
    loaded = client.post("/api/v1/demo/scenario/deepak_acute", headers=headers)
    assert loaded.status_code == 200
    assert "safety" in loaded.json()["phone"]
    reset = client.post("/api/v1/demo/reset", headers=headers)
    assert reset.status_code == 200
    assert reset.json()["seconds"] < 20
    outage = client.post(
        "/api/v1/demo/outage",
        headers=headers,
        json={"provider": "open", "opened": True},
    )
    assert outage.json()["state"] == "open"
    client.post("/api/v1/demo/resilience", headers=headers, json={"enabled": True})
    client.post("/api/v1/demo/warmup", headers=headers)


def test_cost_guard_metrics_and_command_has_no_case_ids() -> None:
    director = _auth("director")
    client.post("/api/v1/demo/cost-exceeded", headers=director)
    kpis = client.get("/api/v1/gov/kpis", headers=_auth("wdec")).json()
    assert kpis["cost_guard"] is True
    assert "cheaper class" in kpis["cost_banner"]
    metrics = client.get("/api/v1/system/metrics", headers=director).json()
    assert "estimated_spend_inr" in metrics
    posture = client.get("/api/v1/command/posture", headers=_auth("commander")).json()
    blob = str(posture)
    assert "MB-4091" not in blob
    assert "MB-6604" not in blob
    copilot = client.post(
        "/api/v1/command/copilot",
        headers=_auth("commander"),
        json={"question": "Charlie Coy mein kaun pareshan hai?", "lang": "hi"},
    )
    assert copilot.status_code == 200
    assert copilot.json()["refuse"] is True
    assert "nahi de sakta" in copilot.json()["answer"]
