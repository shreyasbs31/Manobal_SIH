from __future__ import annotations

import hashlib
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
