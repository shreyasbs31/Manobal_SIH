#!/usr/bin/env python3
"""Measure voice-path latency. Never print secrets."""

from __future__ import annotations

import asyncio
import statistics
import time

from app.config import get_settings
from app.providers.foundry import FoundryClient
from app.voice.tts import synth_sentence


def _pct(samples: list[float], q: float) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    index = min(len(ordered) - 1, int(round(q * (len(ordered) - 1))))
    return ordered[index]


async def main() -> int:
    settings = get_settings()
    client = FoundryClient(settings)
    llm_ms: list[float] = []
    tts_ms: list[float] = []
    combined_ms: list[float] = []
    for _ in range(5):
        started = time.perf_counter()
        await client.chat(
            "fast",
            [{"role": "user", "content": "Reply with one short sentence about rest after duty."}],
            temperature=0,
            max_tokens=128,
            timeout_s=20.0,
        )
        after_llm = time.perf_counter()
        audio, _voice = await synth_sentence("Aapki baat samajh aa rahi hai.", "hi")
        ended = time.perf_counter()
        if not audio:
            continue
        llm_ms.append((after_llm - started) * 1000)
        tts_ms.append((ended - after_llm) * 1000)
        combined_ms.append((ended - started) * 1000)
    if not combined_ms:
        print("no samples")
        return 1
    print(
        "n="
        + str(len(combined_ms))
        + f" llm_p50_ms={_pct(llm_ms, 0.5):.0f} llm_p95_ms={_pct(llm_ms, 0.95):.0f}"
        + f" tts_hi_p50_ms={_pct(tts_ms, 0.5):.0f} tts_hi_p95_ms={_pct(tts_ms, 0.95):.0f}"
        + f" combined_p50_ms={_pct(combined_ms, 0.5):.0f} combined_p95_ms={_pct(combined_ms, 0.95):.0f}"
        + " budget_ms=1800"
    )
    print("combined_samples_ms=" + ",".join(f"{item:.0f}" for item in sorted(combined_ms)))
    return 0 if _pct(combined_ms, 0.5) <= 1800 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
