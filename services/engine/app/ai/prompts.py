from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ..scoring.ruleset import REPO_ROOT, sign_yaml, verify_yaml

PROMPTS_DIR = REPO_ROOT / "infra" / "prompts"

TASK_FILES: dict[str, str] = {
    "companion_turn": "companion.v2.md",
    "crisis_classify": "crisis_classify.md",
    "output_guard": "output_guard.md",
    "checkin_extract": "checkin_extract.md",
    "instrument_conversational": "instrument_conversational.md",
    "case_brief": "case_brief.md",
    "brief_verify": "brief_verify.md",
    "command_copilot": "command_copilot.md",
    "hq_brief": "hq_brief.md",
    "transparency_report": "transparency_report.md",
    "grievance_triage": "grievance_triage.md",
    "translate_ui": "translate_ui.md",
    "conversation_coach": "conversation_coach.md",
}


@dataclass(frozen=True)
class SignedPrompt:
    task: str
    text: str
    signature: bytes
    path: Path


@lru_cache(maxsize=32)
def load_prompt(task: str) -> SignedPrompt:
    filename = TASK_FILES[task]
    path = PROMPTS_DIR / filename
    text = path.read_text(encoding="utf-8")
    signature = sign_yaml(text)
    if not verify_yaml(text, signature):
        raise RuntimeError(f"prompt signature failed for {task}")
    return SignedPrompt(task=task, text=text, signature=signature, path=path)


def bind_user(prompt: str, tag: str, content: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"<{tag}>{content}</{tag}>"},
    ]
