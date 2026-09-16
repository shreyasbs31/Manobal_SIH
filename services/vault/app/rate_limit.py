from __future__ import annotations

import asyncio
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Protocol

from redis.asyncio import Redis


class ResolveRateLimiter(Protocol):
    async def allow(self, actor: str) -> bool: ...

    async def close(self) -> None: ...


LUA_SLIDING_WINDOW = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local member = ARGV[3]
local limit = tonumber(ARGV[4])
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local count = redis.call('ZCARD', key)
if count >= limit then
  return 0
end
redis.call('ZADD', key, now, member)
redis.call('PEXPIRE', key, window)
return 1
"""


class RedisResolveRateLimiter:
    def __init__(self, url: str, *, limit: int, window_seconds: int) -> None:
        self._redis = Redis.from_url(url, decode_responses=False)
        self._limit = limit
        self._window_ms = window_seconds * 1000

    async def allow(self, actor: str) -> bool:
        now_ms = int(time.time() * 1000)
        result = await self._redis.eval(
            LUA_SLIDING_WINDOW,
            1,
            f"vault:resolve:{actor}",
            now_ms,
            self._window_ms,
            f"{now_ms}:{uuid.uuid4()}",
            self._limit,
        )
        return int(result) == 1

    async def close(self) -> None:
        await self._redis.aclose()


class InMemoryResolveRateLimiter:
    def __init__(
        self,
        *,
        limit: int,
        window_seconds: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._limit = limit
        self._window_seconds = window_seconds
        self._clock = clock
        self._events: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def allow(self, actor: str) -> bool:
        now = self._clock()
        async with self._lock:
            events = self._events[actor]
            while events and events[0] <= now - self._window_seconds:
                events.popleft()
            if len(events) >= self._limit:
                return False
            events.append(now)
            return True

    async def close(self) -> None:
        return None
