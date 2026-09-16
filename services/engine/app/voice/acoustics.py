from __future__ import annotations

import os
import time
from typing import Any

import numpy as np

FEATURE_COUNT = 88


def _opensmile_features(pcm: bytes, sample_rate: int) -> list[float] | None:
    if os.environ.get("MANOBAL_OPENSMILE") != "1":
        return None
    try:
        import opensmile
    except ImportError:
        return None
    smile = opensmile.Smile(
        feature_set=opensmile.FeatureSet.eGeMAPSv02,
        feature_level=opensmile.FeatureLevel.Functionals,
    )
    samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    frame = smile.process_signal(samples, sample_rate)
    values = frame.to_numpy().reshape(-1).astype(float).tolist()
    if len(values) >= FEATURE_COUNT:
        return values[:FEATURE_COUNT]
    return values + [0.0] * (FEATURE_COUNT - len(values))


def acoustic_features(pcm: bytes, sample_rate: int = 16000) -> list[float]:
    native = _opensmile_features(pcm, sample_rate)
    if native is not None:
        return native
    samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float64)
    if samples.size == 0:
        return [0.0] * FEATURE_COUNT
    rms = float(np.sqrt(np.mean(samples**2)))
    zcr = float(np.mean(np.abs(np.diff(np.sign(samples)))) / 2)
    centroid = float(np.abs(np.fft.rfft(samples)).argmax()) if samples.size > 8 else 0.0
    base = [rms, zcr, centroid, float(samples.std()), float(samples.mean())]
    tiled = (base * ((FEATURE_COUNT // len(base)) + 1))[:FEATURE_COUNT]
    return tiled


def zeroise(buffer: bytearray) -> int:
    started = time.perf_counter()
    for index in range(len(buffer)):
        buffer[index] = 0
    return int((time.perf_counter() - started) * 1000)


def cleared_event(elapsed_ms: int, features: list[float]) -> dict[str, Any]:
    return {
        "type": "audio.cleared",
        "elapsed_ms": elapsed_ms,
        "feature_count": len(features),
    }
