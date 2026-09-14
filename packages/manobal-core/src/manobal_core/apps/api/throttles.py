"""HTTP rate limits from ``settings.RATE_LIMITS`` (SDD §6.5)."""

from __future__ import annotations

import hashlib
from collections.abc import Callable

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone

_WINDOW = {
    "officer_queue_per_hour": ("/v1/officer/queue", 3600),
    "commander_aggregates_per_hour": ("/v1/commander/aggregates", 3600),
    "captures_batch_per_device_hour": ("/v1/ingest/captures", 3600),
    "integration_webhook_per_minute": ("/v1/integration/", 60),
    "unauthenticated_per_ip_minute": ("*", 60),
    "transcribe_per_hour": ("/v1/me/transcribe", 3600),
}


class RateLimitMiddleware:
    """Refuse callers who exceed the published per-actor ceilings."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        reason = _limited(request)
        if reason is not None:
            return JsonResponse(
                {
                    "type": "about:blank",
                    "title": "Too Many Requests",
                    "status": 429,
                    "code": "MB-4290",
                    "detail": reason,
                },
                status=429,
                content_type="application/problem+json",
            )
        return self.get_response(request)


def _limited(request: HttpRequest) -> str | None:
    if getattr(settings, "RATE_LIMITS_DISABLED", False):
        return None
    path = request.path
    if path.startswith("/dev/"):
        return None
    limits = settings.RATE_LIMITS
    if not isinstance(limits, dict):
        return None
    auth = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth:
        actor = _ip(request)
        ceiling = int(limits.get("unauthenticated_per_ip_minute") or 0)
        if ceiling and _hit(f"rl:ip:{actor}", ceiling, 60):
            return "MB-4290: too many requests"
        return None
    actor = hashlib.sha256(auth.encode()).hexdigest()[:24]
    for key, (prefix, window) in _WINDOW.items():
        if prefix == "*":
            continue
        if path.startswith(prefix):
            ceiling = int(limits.get(key) or 0)
            if ceiling and _hit(f"rl:{key}:{actor}", ceiling, window):
                return "MB-4290: too many requests"
    return None


def _hit(cache_key: str, ceiling: int, window_seconds: int) -> bool:
    now = timezone.now()
    bucket = int(now.timestamp()) // window_seconds
    key = f"{cache_key}:{bucket}"
    added = cache.add(key, 1, timeout=window_seconds + 5)
    if added:
        return False
    try:
        count = int(cache.incr(key))
    except ValueError:
        cache.set(key, 1, timeout=window_seconds + 5)
        return False
    return count > ceiling


def _ip(request: HttpRequest) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    return (request.META.get("REMOTE_ADDR") or "unknown")[:64]
