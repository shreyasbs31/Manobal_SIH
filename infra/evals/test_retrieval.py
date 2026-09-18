from __future__ import annotations

import os

import pytest


@pytest.mark.skipif(os.environ.get("LIVE_EVALS") != "1", reason="retrieval eval needs live embeddings")
async def test_per_language_retrieval_records_choice() -> None:
    from app.ai.corpus import run_retrieval_eval
    from app.scoring.forecast import REGISTRY

    payload = await run_retrieval_eval()
    for lang in ("en", "hi", "hi-Latn", "ta"):
        assert lang in payload["recall_at_3"]
        assert lang in payload["choice"]
    assert REGISTRY["retrieval"]["choice"]["en"] in {"embed", "hash"}
