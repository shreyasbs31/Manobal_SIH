"""Tier-B on-unit inference stub. No transcript is retained."""

from __future__ import annotations

CRISIS_MARKERS = ("kill myself", "end my life", "want to die", "suicid")


def infer_turn(message: str) -> dict[str, str | bool]:
    """Return a reply and whether crisis language was detected.

    A real Tier-B model would run here. The contract is the same: the transcript
    is ephemeral, the reply is content-minimised, and a crisis is a boolean the
    phone uses to trigger SOS — not a diagnosis.
    """
    text = message.lower()
    if any(marker in text for marker in CRISIS_MARKERS):
        return {
            "crisis": True,
            "reply": "Please seek immediate help from welfare or emergency services.",
        }
    from manobal_edge.cloud import complete_chat

    cloud = complete_chat(message)
    return {
        "crisis": False,
        "reply": cloud
        or "I can listen. Use the check-in or talk to welfare if you want support.",
    }
