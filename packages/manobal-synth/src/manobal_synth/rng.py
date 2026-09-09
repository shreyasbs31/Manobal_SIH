"""Label-addressed random substreams.

The determinism requirement is stronger than "seed it once". A single global
generator makes output depend on the order in which subjects happen to be
visited, which breaks the moment anyone parallelises the run or generates one
subject in a test. Every draw here comes from a substream addressed by a stable
label — ``("subject", 417, "physiology")`` — so subject 417's physiology is
identical whether it is generated first, last, or alone.

Nothing in this package touches the legacy ``numpy.random`` global state or the
``random`` module.
"""

from __future__ import annotations

import hashlib

import numpy as np

_DIGEST_BYTES = 16


def _label_entropy(labels: tuple[str | int, ...]) -> int:
    """Hash a label tuple into a stable 128-bit integer.

    Hashed rather than concatenated because ``("a", 1)`` and ``("a1",)`` must not
    collide into the same substream, and Python's ``hash`` is salted per process.
    """
    joined = "\x1f".join(str(part) for part in labels).encode("utf-8")
    return int.from_bytes(hashlib.blake2b(joined, digest_size=_DIGEST_BYTES).digest(), "big")


def substream(seed: int, *labels: str | int) -> np.random.Generator:
    """Return the generator for one addressable substream of ``seed``."""
    entropy = _label_entropy(labels)
    sequence = np.random.SeedSequence(entropy=[seed, entropy])
    return np.random.default_rng(sequence)


def truncated_normal(
    rng: np.random.Generator,
    mean: float,
    sd: float,
    lower: float,
    upper: float,
) -> float:
    """Draw a bounded person-level trait.

    Rejection rather than clipping: clipping piles probability mass on the bounds,
    which would give an implausible number of personnel an exactly-minimal sleep
    baseline and distort the between-person variance the whole personal-baseline
    approach depends on. Twelve attempts then falls back to the midpoint, which is
    unreachable for any sane trait table but keeps the function total.
    """
    if sd <= 0.0:
        return min(max(mean, lower), upper)
    for _ in range(12):
        draw = float(rng.normal(mean, sd))
        if lower <= draw <= upper:
            return draw
    return min(max(mean, lower), upper)


def truncated_lognormal(
    rng: np.random.Generator,
    median: float,
    log_sd: float,
    lower: float,
    upper: float,
) -> float:
    """Draw a bounded positive rate trait.

    Daily hazards (leave applications, transfer requests) are right-skewed across
    a force: most personnel apply rarely, a few apply often. A normal draw would
    need clipping at zero and would understate that tail.
    """
    if log_sd <= 0.0:
        return min(max(median, lower), upper)
    for _ in range(12):
        draw = float(median * np.exp(rng.normal(0.0, log_sd)))
        if lower <= draw <= upper:
            return draw
    return min(max(median, lower), upper)
