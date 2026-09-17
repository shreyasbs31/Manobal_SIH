from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal

import yaml

from ..scoring.ruleset import REPO_ROOT

PROVIDERS_PATH = REPO_ROOT / "infra" / "ai" / "providers.yaml"

PERSONNEL_OR_SAFETY = frozenset(
    {
        "companion_turn",
        "companion_text",
        "companion_voice",
        "crisis_classify",
        "output_guard",
        "checkin_extract",
        "instrument_conversational",
        "grievance_triage",
    }
)

Handler = Callable[[str, dict[str, Any], float], Awaitable["ProviderResponse"]]


class CircuitOpenError(RuntimeError):
    pass


@dataclass
class ProviderResponse:
    text: str
    provider: str
    latency_ms: float
    cached: bool = False
    usage: dict[str, int] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class CircuitBreaker:
    open_after: int = 3
    window_s: float = 60.0
    half_open_after_s: float = 30.0
    failures: list[float] = field(default_factory=list)
    opened_at: float | None = None
    state: Literal["closed", "open", "half_open"] = "closed"

    def allow(self) -> bool:
        now = time.monotonic()
        if self.state == "open":
            if self.opened_at is not None and now - self.opened_at >= self.half_open_after_s:
                self.state = "half_open"
                return True
            return False
        return True

    def record_success(self) -> None:
        self.failures.clear()
        self.opened_at = None
        self.state = "closed"

    def record_failure(self) -> None:
        now = time.monotonic()
        self.failures = [stamp for stamp in self.failures if now - stamp < self.window_s]
        self.failures.append(now)
        if len(self.failures) >= self.open_after:
            self.state = "open"
            self.opened_at = now


@dataclass
class ProviderCallMetric:
    capability: str
    provider: str
    latency_ms: float
    ok: bool
    cached: bool
    at: float


PROVIDER_CALLS: list[ProviderCallMetric] = []
RESILIENCE_CACHE: dict[tuple[str, str], ProviderResponse] = {}
_ROUTER: ProviderRouter | None = None


def load_provider_config() -> dict[str, Any]:
    return yaml.safe_load(PROVIDERS_PATH.read_text(encoding="utf-8"))


class ProviderRouter:
    def __init__(
        self,
        *,
        handlers: dict[str, Handler] | None = None,
        resilience_mode: bool = False,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = load_provider_config()
        self.handlers = handlers or {}
        self.resilience_mode = resilience_mode
        self.now = now
        breaker_cfg = self.config.get("circuit_breaker", {})
        self.breakers: dict[str, CircuitBreaker] = {}
        self._breaker_cfg = {
            "open_after": int(breaker_cfg.get("open_after_failures", 3)),
            "window_s": float(breaker_cfg.get("window_s", 60)),
            "half_open_after_s": float(breaker_cfg.get("half_open_after_s", 30)),
        }

    def _breaker(self, provider: str) -> CircuitBreaker:
        if provider not in self.breakers:
            self.breakers[provider] = CircuitBreaker(**self._breaker_cfg)
        return self.breakers[provider]

    def ordered(self, capability: str) -> list[str]:
        body = self.config["capabilities"].get(capability) or {}
        return [str(item) for item in body.get("ordered", [])]

    def timeout_s(self, capability: str) -> float:
        body = self.config["capabilities"].get(capability) or {}
        return float(body.get("timeout_s", 8.0))

    def fail_safe(self, capability: str) -> str | None:
        body = self.config["capabilities"].get(capability) or {}
        value = body.get("fail_safe")
        return str(value) if value else None

    def assert_alt_allowed(self, capability: str, provider: str) -> None:
        if provider != "alt":
            return
        if capability in PERSONNEL_OR_SAFETY or capability in set(
            self.config.get("personnel_or_safety_tasks", [])
        ):
            raise PermissionError("alt cannot serve personnel or safety tasks")

    async def complete(
        self,
        capability: str,
        payload: dict[str, Any],
        *,
        beat_id: str | None = None,
        language: str = "en",
    ) -> ProviderResponse:
        if self.resilience_mode and beat_id:
            cached = RESILIENCE_CACHE.get((beat_id, language))
            if cached is not None:
                hit = ProviderResponse(
                    text=cached.text,
                    provider=cached.provider,
                    latency_ms=0.0,
                    cached=True,
                    extra=dict(cached.extra),
                )
                PROVIDER_CALLS.append(
                    ProviderCallMetric(capability, hit.provider, 0.0, True, True, self.now())
                )
                return hit

        last_error: Exception | None = None
        prefer = str(payload.get("model_class") or "")
        ordered = self.ordered(capability)
        if prefer in ordered:
            ordered = [prefer] + [name for name in ordered if name != prefer]
        for provider in ordered:
            self.assert_alt_allowed(capability, provider)
            breaker = self._breaker(provider)
            if not breaker.allow():
                last_error = CircuitOpenError(provider)
                continue
            handler = self.handlers.get(provider)
            if handler is None:
                last_error = RuntimeError(f"no handler for {provider}")
                breaker.record_failure()
                continue
            started = self.now()
            try:
                response = await handler(capability, payload, self.timeout_s(capability))
            except Exception as exc:  # noqa: BLE001
                breaker.record_failure()
                last_error = exc
                PROVIDER_CALLS.append(
                    ProviderCallMetric(
                        capability,
                        provider,
                        (self.now() - started) * 1000,
                        False,
                        False,
                        self.now(),
                    )
                )
                continue
            latency = (self.now() - started) * 1000
            if response.latency_ms == 0:
                response.latency_ms = latency
            response.provider = provider
            breaker.record_success()
            PROVIDER_CALLS.append(
                ProviderCallMetric(
                    capability,
                    provider,
                    response.latency_ms,
                    True,
                    False,
                    self.now(),
                )
            )
            if self.resilience_mode and beat_id:
                RESILIENCE_CACHE[(beat_id, language)] = response
            return response

        safe = self.fail_safe(capability)
        if safe == "crisis":
            return ProviderResponse(
                text='{"crisis": true, "confidence": 0.0, "category": "timeout"}',
                provider="fail_safe",
                latency_ms=0.0,
                extra={"crisis": True, "error": True},
            )
        if safe == "block":
            return ProviderResponse(
                text="block",
                provider="fail_safe",
                latency_ms=0.0,
                extra={"block": True, "error": True},
            )
        raise last_error or RuntimeError(f"no provider for {capability}")

    async def warmup(self) -> dict[str, str]:
        status: dict[str, str] = {}
        seen: set[str] = set()
        for _capability, body in self.config["capabilities"].items():
            for provider in body.get("ordered", []):
                name = str(provider)
                if name in seen:
                    continue
                seen.add(name)
                handler = self.handlers.get(name)
                if handler is None:
                    status[name] = "fallback"
                    continue
                try:
                    await handler("warmup", {"text": "ping"}, 1.5)
                    status[name] = "ok"
                except Exception:  # noqa: BLE001
                    status[name] = "error"
        return status


def get_router() -> ProviderRouter:
    global _ROUTER
    if _ROUTER is None:
        from .foundry import build_default_router

        _ROUTER = build_default_router()
    return _ROUTER


def reset_router(router: ProviderRouter | None = None) -> None:
    global _ROUTER
    _ROUTER = router
    PROVIDER_CALLS.clear()
    RESILIENCE_CACHE.clear()
