from __future__ import annotations


def grounded_reply(question: str, chunks: list[dict[str, str]], lang: str) -> tuple[str, list[str]]:
    del question, lang
    if not chunks:
        return (
            "I do not have a reviewed note on that. A welfare officer or counsellor can help.",
            [],
        )
    cites = [item["id"] for item in chunks if "id" in item]
    first = chunks[0]
    text = first.get("text", "")[:220]
    cite = cites[0] if cites else "unknown"
    return (f"{text} [{cite}]", cites)
