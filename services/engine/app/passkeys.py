from __future__ import annotations

import asyncio
import base64
import json
import time
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import cast

from pydantic import BaseModel
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import (
    parse_authentication_credential_json,
    parse_registration_credential_json,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialCreationOptions,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialRequestOptions,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from .auth import (
    PERSONAS,
    DemoLoginRequest,
    LoginResponse,
    Role,
    mint_access_token,
    principal_for_demo,
)
from .config import Settings, get_settings
from .errors import ApiError

JsonObject = dict[str, object]


class ChallengeKind(StrEnum):
    REGISTER = "register"
    LOGIN = "login"


@dataclass(frozen=True)
class Challenge:
    kind: ChallengeKind
    persona_id: str
    challenge: bytes
    expires_at: float


@dataclass
class StoredCredential:
    persona_id: str
    credential_id: bytes
    public_key: bytes
    sign_count: int


class ChallengeStore:
    def __init__(self) -> None:
        self._challenges: dict[str, Challenge] = {}
        self._lock = asyncio.Lock()

    async def put(self, challenge: Challenge) -> str:
        transaction_id = str(uuid.uuid4())
        async with self._lock:
            self._purge_expired()
            self._challenges[transaction_id] = challenge
        return transaction_id

    async def take(self, transaction_id: str, kind: ChallengeKind) -> Challenge:
        async with self._lock:
            self._purge_expired()
            challenge = self._challenges.pop(transaction_id, None)
        if challenge is None or challenge.kind is not kind:
            raise ApiError(
                "passkey_challenge_invalid",
                "The passkey challenge is missing or expired",
                hint="Start the passkey step again",
                status_code=400,
            )
        return challenge

    def _purge_expired(self) -> None:
        now = time.monotonic()
        expired = [
            transaction_id
            for transaction_id, challenge in self._challenges.items()
            if challenge.expires_at <= now
        ]
        for transaction_id in expired:
            self._challenges.pop(transaction_id, None)


class PasskeyOptionsRequest(BaseModel):
    persona_id: str


class PasskeyVerifyRequest(BaseModel):
    transaction_id: str
    credential: JsonObject


class PasskeyOptionsResponse(BaseModel):
    transaction_id: str
    options: JsonObject


challenge_store = ChallengeStore()
credentials: dict[bytes, StoredCredential] = {}


def _persona(persona_id: str) -> object:
    persona = PERSONAS.get(persona_id)
    if persona is None:
        raise ApiError(
            "persona_not_found",
            "The synthetic persona was not found",
            hint="Choose a listed demo persona",
            status_code=404,
        )
    return persona


def _json_options(
    value: PublicKeyCredentialCreationOptions | PublicKeyCredentialRequestOptions,
) -> JsonObject:
    decoded = json.loads(options_to_json(value))
    if not isinstance(decoded, dict):
        raise RuntimeError("Passkey options did not encode to an object")
    return cast(JsonObject, decoded)


async def registration_options(
    request: PasskeyOptionsRequest,
    settings: Settings | None = None,
) -> PasskeyOptionsResponse:
    active_settings = settings or get_settings()
    persona = PERSONAS.get(request.persona_id)
    if persona is None:
        _persona(request.persona_id)
        raise AssertionError("unreachable")
    excluded = [
        PublicKeyCredentialDescriptor(id=credential.credential_id)
        for credential in credentials.values()
        if credential.persona_id == request.persona_id
    ]
    options = generate_registration_options(
        rp_id=active_settings.passkey_rp_id,
        rp_name=active_settings.passkey_rp_name,
        user_id=persona.token.encode("utf-8"),
        user_name=persona.id,
        user_display_name=f"{persona.display_label} Synthetic",
        exclude_credentials=excluded,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
    )
    transaction_id = await challenge_store.put(
        Challenge(
            kind=ChallengeKind.REGISTER,
            persona_id=request.persona_id,
            challenge=options.challenge,
            expires_at=time.monotonic() + active_settings.passkey_challenge_ttl_seconds,
        )
    )
    return PasskeyOptionsResponse(
        transaction_id=transaction_id,
        options=_json_options(options),
    )


async def verify_registration(
    request: PasskeyVerifyRequest,
    settings: Settings | None = None,
) -> LoginResponse:
    active_settings = settings or get_settings()
    challenge = await challenge_store.take(
        request.transaction_id,
        ChallengeKind.REGISTER,
    )
    try:
        parsed = parse_registration_credential_json(json.dumps(request.credential))
        result = verify_registration_response(
            credential=parsed,
            expected_challenge=challenge.challenge,
            expected_rp_id=active_settings.passkey_rp_id,
            expected_origin=active_settings.passkey_origin,
            require_user_verification=True,
        )
    except Exception as error:
        raise ApiError(
            "passkey_verification_failed",
            "The passkey response could not be verified",
            hint="Retry on this device or use the demo sign-in",
            status_code=400,
        ) from error
    credentials[result.credential_id] = StoredCredential(
        persona_id=challenge.persona_id,
        credential_id=result.credential_id,
        public_key=result.credential_public_key,
        sign_count=result.sign_count,
    )
    return mint_access_token(
        principal_for_demo(DemoLoginRequest(role=Role.PERSONNEL, persona_id=challenge.persona_id)),
        active_settings,
    )


async def authentication_options(
    request: PasskeyOptionsRequest,
    settings: Settings | None = None,
) -> PasskeyOptionsResponse:
    active_settings = settings or get_settings()
    _persona(request.persona_id)
    allowed = [
        PublicKeyCredentialDescriptor(id=credential.credential_id)
        for credential in credentials.values()
        if credential.persona_id == request.persona_id
    ]
    options = generate_authentication_options(
        rp_id=active_settings.passkey_rp_id,
        allow_credentials=allowed,
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    transaction_id = await challenge_store.put(
        Challenge(
            kind=ChallengeKind.LOGIN,
            persona_id=request.persona_id,
            challenge=options.challenge,
            expires_at=time.monotonic() + active_settings.passkey_challenge_ttl_seconds,
        )
    )
    return PasskeyOptionsResponse(
        transaction_id=transaction_id,
        options=_json_options(options),
    )


def _credential_id(credential: JsonObject) -> bytes:
    encoded = credential.get("rawId") or credential.get("id")
    if not isinstance(encoded, str):
        raise ApiError(
            "passkey_credential_invalid",
            "The passkey credential id is missing",
            hint="Start the passkey step again",
            status_code=400,
        )
    return base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))


async def verify_authentication(
    request: PasskeyVerifyRequest,
    settings: Settings | None = None,
) -> LoginResponse:
    active_settings = settings or get_settings()
    challenge = await challenge_store.take(
        request.transaction_id,
        ChallengeKind.LOGIN,
    )
    stored = credentials.get(_credential_id(request.credential))
    if stored is None or stored.persona_id != challenge.persona_id:
        raise ApiError(
            "passkey_credential_unknown",
            "This passkey is not registered for the selected persona",
            hint="Register it first or use the demo sign-in",
            status_code=400,
        )
    try:
        parsed = parse_authentication_credential_json(json.dumps(request.credential))
        result = verify_authentication_response(
            credential=parsed,
            expected_challenge=challenge.challenge,
            expected_rp_id=active_settings.passkey_rp_id,
            expected_origin=active_settings.passkey_origin,
            credential_public_key=stored.public_key,
            credential_current_sign_count=stored.sign_count,
            require_user_verification=True,
        )
    except Exception as error:
        raise ApiError(
            "passkey_verification_failed",
            "The passkey response could not be verified",
            hint="Retry on this device or use the demo sign-in",
            status_code=400,
        ) from error
    stored.sign_count = result.new_sign_count
    return mint_access_token(
        principal_for_demo(DemoLoginRequest(role=Role.PERSONNEL, persona_id=challenge.persona_id)),
        active_settings,
    )
