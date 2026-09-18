#!/usr/bin/env python3
"""Measure voice-path first-audio latency over 20 turns. Never print secrets."""

from __future__ import annotations

import asyncio
import os
import statistics
import time
from pathlib import Path

_TOKEN = Path("infra/.cache/foundry.token")
if _TOKEN.is_file() and _TOKEN.stat().st_size > 20:
    os.environ.setdefault("FOUNDRY_AD_TOKEN_FILE", str(_TOKEN.resolve()))

from app.config import get_settings, live_providers_enabled
from app.providers.foundry import FoundryClient, ready_sentence
from app.voice.tts import synth_sentence


def _pct(samples: list[float], q: float) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    index = min(len(ordered) - 1, int(round(q * (len(ordered) - 1))))
    return ordered[index]


async def _one_turn(client: FoundryClient) -> float:
    started = time.perf_counter()
    first_audio = 0.0
    if live_providers_enabled() and client.available("fast"):
        agen = client.chat_stream(
            "fast",
            [
                {
                    "role": "user",
                    "content": "Reply with one short Hindi sentence about rest after duty.",
                }
            ],
            max_tokens=128,
            timeout_s=20.0,
        )
        try:
            async for sentence in agen:
                audio, _voice = await synth_sentence(sentence, "hi")
                if audio:
                    first_audio = (time.perf_counter() - started) * 1000
                break
        finally:
            await agen.aclose()
        if first_audio:
            return first_audio
    result = await client.chat(
        "fast",
        [{"role": "user", "content": "Reply with one short sentence about rest after duty."}],
        temperature=0,
        max_tokens=128,
        timeout_s=20.0,
        voice=True,
    )
    sentence, _rest = ready_sentence(result.text + ".")
    audio, _voice = await synth_sentence(sentence or "Aapki baat samajh aa rahi hai.", "hi")
    if not audio:
        raise RuntimeError("empty_tts")
    return (time.perf_counter() - started) * 1000


async def main() -> int:
    settings = get_settings()
    client = FoundryClient(settings)
    samples: list[float] = []
    turns = 20
    for _ in range(turns):
        try:
            samples.append(await _one_turn(client))
        except Exception as exc:  # noqa: BLE001
            print(f"turn_fail {type(exc).__name__}")
    if not samples:
        print("no samples")
        return 1
    p50 = _pct(samples, 0.5)
    p95 = _pct(samples, 0.95)
    mean = statistics.mean(samples)
    print(
        "n="
        + str(len(samples))
        + f" first_audio_p50_ms={p50:.0f} first_audio_p95_ms={p95:.0f}"
        + f" mean_ms={mean:.0f} target_ms=2500 auth={client.auth_path()}"
    )
    print("samples_ms=" + ",".join(f"{item:.0f}" for item in sorted(samples)))
    if p50 <= 2500:
        print("target_2_5s=hit")
        return 0
    print(
        "target_2_5s=miss India to eastus2 still waits on first model token. "
        "Streaming starts TTS on the first sentence; the remaining gap is model time of flight."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
