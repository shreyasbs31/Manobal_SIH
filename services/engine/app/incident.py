from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field

from .auth import PERSONAS
from .privacy.kanon import commander_incident_card

INCIDENT_CARDS: dict[str, IncidentWindow] = {}
TALK_REQUESTS: list[dict[str, str]] = []


class IncidentWebhook(BaseModel):
    unit_path: str
    type: str = Field(pattern=r"^(encounter|ied|casualty|colleague_death|accident|disaster)$")
    occurred_at: datetime
    severity: int = Field(ge=1, le=5)
    nonce: str
    timestamp: int


@dataclass
class IncidentWindow:
    id: str
    unit_path: str
    type: str
    opened_at: datetime
    closes_at: datetime
    followup_at: datetime
    asked_to_talk: int = 0
    enrolled: int = 0
    cards_issued: int = 0


USED_NONCES: set[str] = set()


def verify_hmac(secret: str, body: bytes, signature: str, timestamp: int, nonce: str) -> None:
    if nonce in USED_NONCES:
        raise ValueError("replay")
    if abs(int(time.time()) - timestamp) > 300:
        raise ValueError("stale")
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError("bad_signature")
    USED_NONCES.add(nonce)


def open_incident(payload: IncidentWebhook, enrolled: int = 100) -> IncidentWindow:
    opened = payload.occurred_at.astimezone(UTC)
    window = IncidentWindow(
        id=f"inc-{payload.unit_path}-{int(opened.timestamp())}",
        unit_path=payload.unit_path,
        type=payload.type,
        opened_at=opened,
        closes_at=opened + timedelta(hours=72),
        followup_at=opened + timedelta(days=28),
        enrolled=enrolled,
        cards_issued=enrolled,
    )
    INCIDENT_CARDS[window.id] = window
    return window


def request_to_talk(window_id: str, token: str) -> None:
    window = INCIDENT_CARDS[window_id]
    TALK_REQUESTS.append({"window_id": window_id, "token": token, "unit_path": window.unit_path})
    window.asked_to_talk += 1


def uwo_board(unit_path: str) -> list[dict[str, str]]:
    return [row for row in TALK_REQUESTS if row["unit_path"].startswith(unit_path)]


def commander_card(window: IncidentWindow) -> dict[str, str | int | None]:
    return commander_incident_card(
        enrolled=window.enrolled,
        asked=window.asked_to_talk,
        open_until=window.closes_at.isoformat(),
        followup=window.followup_at.isoformat(),
    )


def lalit_demo_window() -> IncidentWindow:
    persona = PERSONAS["lalit"]
    payload = IncidentWebhook(
        unit_path=persona.unit_path,
        type="ied",
        occurred_at=datetime(2026, 9, 13, 6, 0, tzinfo=UTC),
        severity=4,
        nonce="lalit-demo",
        timestamp=int(time.time()),
    )
    window = open_incident(payload, enrolled=100)
    request_to_talk(window.id, persona.token)
    return window
