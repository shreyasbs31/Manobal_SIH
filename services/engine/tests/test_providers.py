from __future__ import annotations

import asyncio

import pytest
from app.providers.router import (
    PROVIDER_CALLS,
    RESILIENCE_CACHE,
    CircuitOpenError,
    ProviderResponse,
    ProviderRouter,
    reset_router,
)


def _router(handlers: dict, *, resilience: bool = False) -> ProviderRouter:
    reset_router()
    return ProviderRouter(handlers=handlers, resilience_mode=resilience)


async def test_timeout_falls_through_and_classifier_is_crisis() -> None:
    async def boom(capability: str, payload: dict, timeout_s: float) -> ProviderResponse:
        del capability, payload
        await asyncio.sleep(timeout_s + 0.01)
        raise TimeoutError("slow")

    async def wrapped(capability: str, payload: dict, timeout_s: float) -> ProviderResponse:
        return await asyncio.wait_for(boom(capability, payload, timeout_s), timeout=timeout_s)

    router = _router({"fast": wrapped, "main": wrapped})
    result = await router.complete("crisis_classify", {"text": "hello"})
    assert result.extra["crisis"] is True
    assert result.provider == "fail_safe"


async def test_circuit_opens_after_three_failures() -> None:
    calls = {"n": 0}

    async def fail(capability: str, payload: dict, timeout_s: float) -> ProviderResponse:
        del capability, payload, timeout_s
        calls["n"] += 1
        raise RuntimeError("down")

    router = _router({"fast": fail, "main": fail})
    for _ in range(3):
        result = await router.complete("crisis_classify", {"text": "x"})
        assert result.extra["crisis"] is True
    assert router._breaker("fast").state == "open"
    with pytest.raises(CircuitOpenError):
        if not router._breaker("fast").allow():
            raise CircuitOpenError("fast")
    before = calls["n"]
    again = await router.complete("crisis_classify", {"text": "x"})
    assert again.extra["crisis"] is True
    assert calls["n"] == before


async def test_alt_blocked_on_personnel_tasks() -> None:
    async def alt(capability: str, payload: dict, timeout_s: float) -> ProviderResponse:
        del capability, payload, timeout_s
        return ProviderResponse(text="nope", provider="alt", latency_ms=1)

    router = _router({"alt": alt})
    router.config["capabilities"]["companion_text"]["ordered"] = ["alt"]
    with pytest.raises(PermissionError):
        await router.complete("companion_text", {"text": "hi"})


async def test_payload_model_class_is_tried_first() -> None:
    order: list[str] = []

    async def open_h(capability: str, payload: dict, timeout_s: float) -> ProviderResponse:
        del capability, payload, timeout_s
        order.append("open")
        return ProviderResponse(text="open", provider="open", latency_ms=1)

    async def main_h(capability: str, payload: dict, timeout_s: float) -> ProviderResponse:
        del capability, payload, timeout_s
        order.append("main")
        return ProviderResponse(text="main", provider="main", latency_ms=1)

    router = _router({"open": open_h, "main": main_h})
    result = await router.complete(
        "companion_text", {"text": "x", "model_class": "main"}
    )
    assert result.provider == "main"
    assert order[0] == "main"


async def test_resilience_cache_keyed_by_beat_and_language() -> None:
    n = {"calls": 0}

    async def once(capability: str, payload: dict, timeout_s: float) -> ProviderResponse:
        del capability, timeout_s
        n["calls"] += 1
        return ProviderResponse(text=str(payload.get("text")), provider="open", latency_ms=12)

    router = _router({"open": once, "main": once}, resilience=True)
    first = await router.complete("companion_text", {"text": "beat"}, beat_id="s05", language="hi")
    second = await router.complete(
        "companion_text", {"text": "ignored"}, beat_id="s05", language="hi"
    )
    other = await router.complete(
        "companion_text", {"text": "en beat"}, beat_id="s05", language="en"
    )
    assert first.text == "beat"
    assert second.cached is True
    assert second.text == "beat"
    assert other.cached is False
    assert n["calls"] == 2
    assert ("s05", "hi") in RESILIENCE_CACHE


async def test_warmup_reports_ok_or_fallback() -> None:
    async def ok(capability: str, payload: dict, timeout_s: float) -> ProviderResponse:
        del capability, payload, timeout_s
        return ProviderResponse(text="ok", provider="fast", latency_ms=1)

    router = _router({"fast": ok, "main": ok, "open": ok})
    status = await router.warmup()
    assert status["fast"] == "ok"
    assert "deepgram_nova3_en" in status
    assert status["deepgram_nova3_en"] == "fallback"
    assert PROVIDER_CALLS or status


def test_warmup_endpoint_and_provider_metrics() -> None:
    from app.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    director = client.post("/api/v1/auth/demo-login", json={"role": "director"}).json()
    wdec = client.post("/api/v1/auth/demo-login", json={"role": "wdec"}).json()
    warm = client.post(
        "/api/v1/demo/warmup",
        headers={"authorization": f"Bearer {director['access_token']}"},
    )
    assert warm.status_code == 200, warm.text
    body = warm.json()
    assert "fast" in body
    assert body["fast"] in {"ok", "fallback", "error"}
    metrics = client.get(
        "/api/v1/gov/providers",
        headers={"authorization": f"Bearer {wdec['access_token']}"},
    )
    assert metrics.status_code == 200
    payload = metrics.json()
    assert "companion_text" in payload["capabilities"]
    assert payload["foundry_configured"] is False
