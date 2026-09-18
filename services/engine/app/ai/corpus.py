from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import numpy as np

from ..scoring.ruleset import REPO_ROOT
from .corpus_data import DOCS

CORPUS_DIR = REPO_ROOT / "infra" / "corpus"
EMBED_DIM = 1024


@dataclass
class Chunk:
    id: str
    doc_id: str
    lang: str
    title: str
    text: str
    version: str
    embedding: np.ndarray


CHUNKS: list[Chunk] = []
EMBED_CHOICE: dict[str, str] = {"en": "hash", "hi": "hash", "hi-Latn": "hash", "ta": "hash"}
LIVE_EMBEDDED = False


def hash_embedding(text: str, dims: int = EMBED_DIM) -> np.ndarray:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    seed = int.from_bytes(digest[:8], "big")
    rng = np.random.default_rng(seed)
    vec = rng.normal(size=dims)
    norm = np.linalg.norm(vec)
    if norm:
        vec = vec / norm
    return vec.astype(np.float64)


def _chunk_text(text: str, size: int = 400) -> list[str]:
    words = text.split()
    if not words:
        return [text]
    pieces: list[str] = []
    for start in range(0, len(words), size):
        pieces.append(" ".join(words[start : start + size]))
    return pieces


def write_markdown() -> None:
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    marker = CORPUS_DIR / "sleep-rotating-en.md"
    if marker.exists():
        return
    for doc in DOCS:
        for lang in ("en", "hi"):
            title = doc["title_en"] if lang == "en" else doc["title_hi"]
            body = doc[lang]
            path = CORPUS_DIR / f"{doc['id']}-{lang}.md"
            path.write_text(
                (
                    f"---\n"
                    f"id: {doc['id']}\n"
                    f"title: {title}\n"
                    f"lang: {lang}\n"
                    f"reviewed_by: team\n"
                    f"version: 1\n"
                    f"---\n\n"
                    f"{body}\n"
                ),
                encoding="utf-8",
            )


def embed_corpus() -> list[Chunk]:
    write_markdown()
    CHUNKS.clear()
    for doc in DOCS:
        for lang in ("en", "hi"):
            for index, piece in enumerate(_chunk_text(doc[lang]), start=1):
                chunk_id = f"{doc['id']}-{lang}#{index}"
                CHUNKS.append(
                    Chunk(
                        id=chunk_id,
                        doc_id=doc["id"],
                        lang=lang,
                        title=doc["title_en"] if lang == "en" else doc["title_hi"],
                        text=piece,
                        version="1",
                        embedding=hash_embedding(piece),
                    )
                )
    return CHUNKS


def retrieve(question: str, lang: str, k: int = 3) -> list[Chunk]:
    if not CHUNKS:
        embed_corpus()
    wanted = "hi" if lang.startswith("hi") else "en"
    pool = [chunk for chunk in CHUNKS if chunk.lang == wanted] or CHUNKS
    stop = {
        "the",
        "and",
        "for",
        "you",
        "can",
        "with",
        "that",
        "this",
        "what",
        "how",
        "should",
        "after",
        "from",
        "have",
        "not",
        "are",
        "was",
        "your",
    }
    tokens = {
        token
        for token in question.lower().split()
        if len(token) > 3 and token not in stop
    }
    scored: list[tuple[int, Chunk]] = []
    for chunk in pool:
        words = {
            token
            for token in chunk.text.lower().split()
            if len(token) > 3 and token not in stop
        }
        scored.append((len(tokens.intersection(words)), chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for overlap, chunk in scored[:k] if overlap >= 2]


def embedding_class_for(lang: str) -> str:
    if lang.startswith("en"):
        return "embed"
    return "embed_ml"


def _cosine(left: np.ndarray, right: np.ndarray) -> float:
    denom = float(np.linalg.norm(left) * np.linalg.norm(right))
    if denom == 0:
        return 0.0
    return float(np.dot(left, right) / denom)


async def embed_corpus_live() -> str:
    from ..config import live_providers_enabled
    from ..providers.foundry import FoundryClient

    global LIVE_EMBEDDED
    write_markdown()
    if not live_providers_enabled():
        embed_corpus()
        return "hash"
    client = FoundryClient()
    if not client.available("embeddings"):
        embed_corpus()
        return "hash"
    embed_corpus()
    en_texts = [chunk.text for chunk in CHUNKS if chunk.lang == "en"]
    hi_texts = [chunk.text for chunk in CHUNKS if chunk.lang == "hi"]
    try:
        en_vecs = await client.embed(en_texts or ["ping"], 30.0, model_class="embed")
        ml_class = "embed_ml" if client.available("embed_ml") else "embed"
        hi_vecs = await client.embed(hi_texts or ["ping"], 30.0, model_class=ml_class)
    except Exception:  # noqa: BLE001
        return "hash"
    en_i = 0
    hi_i = 0
    for chunk in CHUNKS:
        if chunk.lang == "en" and en_i < len(en_vecs):
            chunk.embedding = np.array(en_vecs[en_i], dtype=np.float64)
            en_i += 1
        elif chunk.lang == "hi" and hi_i < len(hi_vecs):
            chunk.embedding = np.array(hi_vecs[hi_i], dtype=np.float64)
            hi_i += 1
    EMBED_CHOICE["en"] = "embed"
    EMBED_CHOICE["hi"] = ml_class
    EMBED_CHOICE["hi-Latn"] = ml_class
    EMBED_CHOICE["ta"] = ml_class
    LIVE_EMBEDDED = True
    try:
        _ = await client.rerank("sleep after night duty", en_texts[:8], 20.0)
        EMBED_CHOICE["rerank"] = "rerank"
    except Exception:  # noqa: BLE001
        EMBED_CHOICE["rerank"] = "none"
    return "live"


async def retrieve_live(question: str, lang: str, k: int = 3) -> list[Chunk]:
    from ..config import live_providers_enabled
    from ..providers.foundry import FoundryClient

    if not LIVE_EMBEDDED:
        await embed_corpus_live()
    if lang.startswith("hi-Latn"):
        from .transliterate import transliterate_hi

        question = await transliterate_hi(question)
        lang = "hi"
    lexical = retrieve(question, lang, k=max(k, 6))
    if not live_providers_enabled() or not LIVE_EMBEDDED:
        return lexical[:k]
    wanted = "hi" if lang.startswith("hi") else "en"
    pool = [chunk for chunk in CHUNKS if chunk.lang == wanted] or CHUNKS
    if lang.startswith("ta"):
        pool = CHUNKS
    client = FoundryClient()
    model_class = embedding_class_for(lang)
    try:
        vectors = await client.embed([question], 20.0, model_class=model_class)
        query_vec = np.array(vectors[0], dtype=np.float64)
    except Exception:  # noqa: BLE001
        return lexical[:k]
    ranked = sorted(pool, key=lambda chunk: _cosine(query_vec, chunk.embedding), reverse=True)
    top = ranked[:10]
    try:
        order = await client.rerank(question, [chunk.text for chunk in top], 12.0)
        ordered = [top[i] for i in order if 0 <= i < len(top)]
        if ordered:
            top = ordered
    except Exception:  # noqa: BLE001
        pass
    merged: list[Chunk] = []
    seen: set[str] = set()
    for chunk in top + lexical:
        if chunk.id in seen:
            continue
        seen.add(chunk.id)
        merged.append(chunk)
        if len(merged) >= k:
            break
    return merged


EVAL_QUESTIONS: dict[str, list[dict[str, str]]] = {
    "en": [{"q": "How should I sleep after night duty on rotating shifts?", "doc": "sleep-rotating"}],
    "hi": [{"q": "रात की ड्यूटी के बाद नींद कैसे पूरी करें?", "doc": "sleep-rotating"}],
    "hi-Latn": [{"q": "raat ki duty ke baad neend kaise poori karein?", "doc": "sleep-rotating"}],
    "ta": [{"q": "இரவு டியூட்டிக்கு பிறகு எப்படி தூங்குவது?", "doc": "sleep-rotating"}],
}


async def run_retrieval_eval() -> dict[str, object]:
    from ..scoring.forecast import REGISTRY, register_world_metrics
    from ..scoring.ruleset import REPO_ROOT

    method = await embed_corpus_live()
    scores: dict[str, float] = {}
    for lang, rows in EVAL_QUESTIONS.items():
        hits = 0
        for row in rows:
            found = await retrieve_live(row["q"], lang, k=3)
            if any(chunk.doc_id == row["doc"] for chunk in found):
                hits += 1
        scores[lang] = hits / max(1, len(rows))
    payload = {
        "method": method,
        "choice": dict(EMBED_CHOICE),
        "recall_at_3": scores,
    }
    register_world_metrics("retrieval", scores, version=f"retrieval-{method}")
    REGISTRY["retrieval"]["choice"] = dict(EMBED_CHOICE)
    REGISTRY["retrieval"]["method"] = method
    path = REPO_ROOT / "infra" / "evals" / "fixtures" / "retrieval.json"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass
    return payload


def grounded_reply(
    question: str, chunks: list[dict[str, str]], lang: str
) -> tuple[str, list[str]]:
    found = chunks or [
        {"id": chunk.id, "text": chunk.text} for chunk in retrieve(question, lang)
    ]
    if not found:
        offer = (
            "उस पर समीक्षित नोट नहीं है. कल्याण अधिकारी या परामर्शदाता मदद कर सकते हैं."
            if lang.startswith("hi")
            else "I do not have a reviewed note on that. A welfare officer or counsellor can help."
        )
        return (offer, [])
    cites = [item["id"] for item in found[:3] if "id" in item]
    text = found[0].get("text", "")[:220]
    cite = cites[0] if cites else found[0].get("id", "unknown")
    return (f"{text} [{cite}]", cites)


def counts() -> dict[str, int]:
    write_markdown()
    en = len(list(CORPUS_DIR.glob("*-en.md")))
    hi = len(list(CORPUS_DIR.glob("*-hi.md")))
    return {"en": en, "hi": hi, "topics": len(DOCS)}
