from __future__ import annotations

from pathlib import Path


def test_eval_harness_is_reserved_for_later_phases() -> None:
    root = Path(__file__).resolve().parent
    assert root.name == "evals"
    assert (root / "test_harness.py").exists()
