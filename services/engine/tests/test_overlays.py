from __future__ import annotations

from app.scoring.overlays import compute_overlays


def test_overlays_are_computed_not_literals() -> None:
    overlay = compute_overlays()
    assert overlay["source"] in {"core.assessment", "demo_cases_memory"}
    if overlay["source"] == "demo_cases_memory":
        assert float(overlay["metrics"]["precision"]) > 0
    labels = {row["code"] for row in overlay["kpis"]}
    assert {"K1", "K3", "K10", "K11", "K12"} <= labels
    assert "Imran stays" in overlay["personas"]["imran"]
    assert "Thomas stays" in overlay["personas"]["thomas"]
    for row in overlay["kpis"]:
        if row["code"] == "K1":
            assert row["value"] != "4.2 d"
