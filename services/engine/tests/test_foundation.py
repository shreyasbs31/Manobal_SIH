from __future__ import annotations

import inspect

from app.auth import (
    PERSONAS,
    ROLE_SCOPES,
    DemoLoginRequest,
    Role,
    decode_access_token,
    mint_access_token,
    principal_for_demo,
)
from app.logging import REDACTED, redact_pii
from app.main import app
from app.pagination import decode_cursor, encode_cursor
from app.security import RowPredicate, ltree_predicate
from app.sim_clock import wall_seconds_for_sla
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

client = TestClient(app)

ROLES = tuple(role.value for role in Role)
PERSONA_IDS = tuple(PERSONAS)


def test_engine_root_points_at_the_web_app() -> None:
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "manobal-engine"
    assert payload["app"] == "http://localhost:3000"
    assert "access token" in payload["note"].lower()


def test_demo_login_mints_every_role() -> None:
    for role in ROLES:
        body: dict[str, str] = {"role": role}
        if role == "personnel":
            body["persona_id"] = "arjun"
        response = client.post("/api/v1/auth/demo-login", json=body)
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["token_type"] == "bearer"
        assert payload["expires_in"] == 900
        principal = payload["principal"]
        assert principal["role"] == role
        assert principal["synthetic"] is True
        if role == "personnel":
            assert principal["subject_token"] == PERSONAS["arjun"].token
        else:
            assert principal["subject_token"] is None


def test_demo_login_mints_every_persona() -> None:
    for persona_id in PERSONA_IDS:
        response = client.post(
            "/api/v1/auth/demo-login",
            json={"role": "personnel", "persona_id": persona_id},
        )
        assert response.status_code == 200, response.text
        principal = response.json()["principal"]
        persona = PERSONAS[persona_id]
        assert principal["subject_token"] == persona.token
        assert principal["scope_path"] == persona.unit_path


def test_error_envelope_on_missing_token() -> None:
    response = client.post("/api/v1/gov/audit/verify")
    assert response.status_code == 401
    error = response.json()["error"]
    assert error["code"] == "authentication_required"
    assert "hint" in error
    assert "trace_id" in error
    assert response.headers["x-trace-id"] == error["trace_id"]


def test_command_and_hq_routes_omit_person_parameters() -> None:
    forbidden = {
        "token",
        "case",
        "case_id",
        "person",
        "person_id",
        "subject_token",
        "service_no",
    }
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not (route.path.startswith("/api/v1/command") or route.path.startswith("/api/v1/hq")):
            continue
        path_lower = route.path.lower()
        for name in forbidden:
            assert f"{{{name}}}" not in path_lower
        for parameter in inspect.signature(route.endpoint).parameters:
            assert parameter.lower() not in forbidden


def test_role_scopes_are_partitioned() -> None:
    assert "command:aggregate" in ROLE_SCOPES[Role.COMMANDER]
    assert "gov:read" in ROLE_SCOPES[Role.WDEC]
    assert "demo:write" in ROLE_SCOPES[Role.DIRECTOR]
    assert "welfare:write" not in ROLE_SCOPES[Role.COMMANDER]
    assert "me:read" not in ROLE_SCOPES[Role.HQ]


def test_access_token_roundtrip() -> None:
    login = mint_access_token(principal_for_demo(DemoLoginRequest(role=Role.UWO)))
    assert login.expires_in == 900
    principal = decode_access_token(login.access_token)
    assert principal.role is Role.UWO
    assert principal.subject_token is None


def test_signed_cursor_roundtrip() -> None:
    encoded = encode_cursor({"id": "MB-4091", "opened_at": "2026-09-16T04:30:00+00:00"})
    decoded = decode_cursor(encoded)
    assert decoded["id"] == "MB-4091"


def test_ltree_predicate_is_parameterised() -> None:
    clause = str(ltree_predicate("unit_path", RowPredicate.UNIT_SUBTREE))
    assert ":scope_path" in clause
    assert "unit_path" in clause


def test_sla_uses_wall_time_compression() -> None:
    assert wall_seconds_for_sla(3600) == 60


def test_logs_redact_service_numbers_and_names() -> None:
    redacted = redact_pii(
        None,
        "info",
        {
            "event": "check_in",
            "name": "Ct/GD Arjun Rathore",
            "note": "Called SYN-4091 from 9876543210",
        },
    )
    assert redacted["name"] == REDACTED
    assert REDACTED in str(redacted["note"])
    assert "9876543210" not in str(redacted["note"])
    assert "SYN-4091" not in str(redacted["note"])
