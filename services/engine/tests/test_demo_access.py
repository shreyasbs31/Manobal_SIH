from __future__ import annotations

import pytest
from app.auth import Role
from app.config import Settings
from app.demo_access import (
    DemoGateLevel,
    access_code_matches,
    decode_demo_gate,
    make_access_code_hash,
    mint_demo_gate,
    require_demo_role,
    validate_demo_gate_settings,
)
from app.errors import ApiError
from fastapi import Request
from pydantic import SecretStr


def _settings(**updates: object) -> Settings:
    values: dict[str, object] = {
        "demo_gate_required": True,
        "demo_gate_access_hash": SecretStr(make_access_code_hash("judge-code-123")),
        "demo_gate_operator_hash": SecretStr(make_access_code_hash("operator-code-123")),
        "demo_gate_jwt_secret": SecretStr("gate_test_secret_that_is_at_least_32_bytes"),
        "demo_gate_cookie_name": "manobal.demo_gate",
        "demo_gate_minutes": 60,
    }
    values.update(updates)
    return Settings.model_construct(**values)


def _request(cookie: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if cookie:
        headers.append((b"cookie", cookie.encode("utf-8")))
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": headers,
            "client": ("127.0.0.1", 1234),
        }
    )


def test_access_code_hash_round_trip() -> None:
    encoded = make_access_code_hash("judge-code-123", salt=b"1" * 16)
    assert access_code_matches("judge-code-123", encoded)
    assert not access_code_matches("wrong-code-123", encoded)
    assert not access_code_matches("judge-code-123", "not-a-supported-hash")


def test_gate_token_round_trip_and_operator_roles() -> None:
    settings = _settings()
    judge_token, expires_in = mint_demo_gate(DemoGateLevel.JUDGE, settings)
    assert expires_in == 3600
    assert decode_demo_gate(judge_token, settings) is DemoGateLevel.JUDGE
    request = _request(f"{settings.demo_gate_cookie_name}={judge_token}")
    assert require_demo_role(request, Role.COMMANDER, settings) is DemoGateLevel.JUDGE
    with pytest.raises(ApiError) as error:
        require_demo_role(request, Role.DIRECTOR, settings)
    assert error.value.code == "operator_access_required"


def test_operator_token_can_use_director() -> None:
    settings = _settings()
    token, _ = mint_demo_gate(DemoGateLevel.OPERATOR, settings)
    request = _request(f"{settings.demo_gate_cookie_name}={token}")
    assert require_demo_role(request, Role.DIRECTOR, settings) is DemoGateLevel.OPERATOR


def test_required_gate_validates_all_secret_names() -> None:
    settings = _settings(
        demo_gate_access_hash=SecretStr(""),
        demo_gate_operator_hash=SecretStr(""),
        demo_gate_jwt_secret=SecretStr("short"),
    )
    with pytest.raises(RuntimeError) as error:
        validate_demo_gate_settings(settings)
    message = str(error.value)
    assert "DEMO_GATE_ACCESS_HASH" in message
    assert "DEMO_GATE_OPERATOR_HASH" in message
    assert "DEMO_GATE_JWT_SECRET" in message
