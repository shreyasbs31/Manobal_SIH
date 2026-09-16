from __future__ import annotations

import base64
import hashlib
import hmac
import json
from collections.abc import Mapping

from pydantic import BaseModel, Field

from .config import get_settings
from .errors import ApiError

type CursorScalar = str | int | float | bool | None


class CursorPage[T](BaseModel):
    items: list[T]
    next_cursor: str | None = None


class PageQuery(BaseModel):
    cursor: str | None = None
    limit: int = Field(default=50, ge=1, le=100)


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def encode_cursor(values: Mapping[str, CursorScalar]) -> str:
    payload = json.dumps(
        {"v": 1, "values": dict(values)},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    secret = get_settings().access_jwt_secret.get_secret_value().encode("utf-8")
    signature = hmac.new(secret, payload, hashlib.sha256).digest()
    return f"{_b64encode(payload)}.{_b64encode(signature)}"


def decode_cursor(cursor: str) -> dict[str, CursorScalar]:
    try:
        encoded_payload, encoded_signature = cursor.split(".", maxsplit=1)
        payload = _b64decode(encoded_payload)
        supplied_signature = _b64decode(encoded_signature)
        secret = get_settings().access_jwt_secret.get_secret_value().encode("utf-8")
        expected_signature = hmac.new(secret, payload, hashlib.sha256).digest()
        if not hmac.compare_digest(supplied_signature, expected_signature):
            raise ValueError("signature")
        decoded = json.loads(payload)
        if decoded.get("v") != 1 or not isinstance(decoded.get("values"), dict):
            raise ValueError("version")
        values: dict[str, CursorScalar] = {}
        for key, value in decoded["values"].items():
            if not isinstance(key, str) or not (
                value is None or isinstance(value, (str, int, float, bool))
            ):
                raise ValueError("shape")
            values[key] = value
        return values
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        raise ApiError(
            "invalid_cursor",
            "The pagination cursor is invalid or expired",
            hint="Start again without a cursor",
            status_code=400,
        ) from error
