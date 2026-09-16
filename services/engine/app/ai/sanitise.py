from __future__ import annotations

import re

ROLE_RE = re.compile(
    r"(?i)(system\s*:|assistant\s*:|ignore previous|ignore all instructions|"
    r"<\|im_start\|>|developer mode|you are now)"
)
MARKUP_RE = re.compile(r"[<>]")


def sanitise(text: str, *, limit: int = 1000) -> str:
    cleaned = ROLE_RE.sub(" ", text)
    cleaned = MARKUP_RE.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:limit]
