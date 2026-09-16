from __future__ import annotations

from app.ai.corpus import counts, embed_corpus, grounded_reply, retrieve
from app.ai.pipeline import run_pipeline


def test_corpus_has_twenty_five_to_thirty_docs_each_language() -> None:
    totals = counts()
    assert 25 <= totals["en"] <= 30
    assert 25 <= totals["hi"] <= 30
    assert totals["en"] == totals["hi"] == totals["topics"]
    chunks = embed_corpus()
    assert any(chunk.id.endswith("#1") for chunk in chunks)
    assert all(chunk.embedding.shape == (1024,) for chunk in chunks)


async def test_ask_mode_cites_chunk_ids_for_in_corpus_question() -> None:
    hits = retrieve("How should I sleep after night duty on rotating shifts?", "en")
    result = await run_pipeline(
        "How should I sleep after night duty on rotating shifts?",
        lang="en",
        mode="ask",
        chunks=[{"id": chunk.id, "text": chunk.text} for chunk in hits],
    )
    assert result.model_reached is True
    assert result.citations
    assert result.reply
    assert any(cite in result.reply for cite in result.citations)


async def test_ask_outside_corpus_offers_a_person() -> None:
    reply, cites = grounded_reply(
        "What is the capital of Australia and the cricket score?",
        [],
        "en",
    )
    assert cites == []
    assert "welfare officer" in reply.lower() or "counsellor" in reply.lower()
    assert "Australia" not in reply
