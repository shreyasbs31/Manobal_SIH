from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
import pytest
from app.config import Settings
from app.crypto import decrypt_identity, encrypt_identity, subject_token
from app.errors import ApiError
from app.grants import verify_grant
from app.key_provider import LocalKeyProvider
from app.rate_limit import InMemoryResolveRateLimiter

ROOT = Path(__file__).resolve().parents[3]
PERSONAS = (
    ("SYN-4091", "st_364aifljnxnxpqzk"),
    ("SYN-2217", "st_54dhr3kdu3njopjr"),
    ("SYN-3380", "st_knqon22p4ahp64uu"),
    ("SYN-1506", "st_xxvoccg2lkivzgxk"),
    ("SYN-5120", "st_pa3bwrpt2mffj52y"),
    ("SYN-6604", "st_ahe6nh4uupnem2wp"),
    ("SYN-7342", "st_kar3rtglz3ydm7uh"),
    ("SYN-8815", "st_gmtgrj5q2fihzscl"),
)


needs_project_token_key = pytest.mark.skipif(
    os.environ.get("MANOBAL_CI_RANDOM_KEYS") == "1",
    reason="Persona tokens derive from the project's private dev token key; CI has a random one.",
)


def local_settings() -> Settings:
    return Settings(
        local_key_file=ROOT / "infra/keys/dev-vault-keys.json",
        grant_public_key_file=ROOT / "infra/keys/grant-public.pem",
    )


@pytest.fixture
def provider() -> LocalKeyProvider:
    return LocalKeyProvider(local_settings())


@needs_project_token_key
@pytest.mark.parametrize(("service_no", "token"), PERSONAS)
async def test_tokens_are_deterministic(
    provider: LocalKeyProvider,
    service_no: str,
    token: str,
) -> None:
    assert await subject_token(service_no, provider) == token


@needs_project_token_key
async def test_identity_roundtrip_keeps_fields_token_bound(
    provider: LocalKeyProvider,
) -> None:
    encrypted = await encrypt_identity(
        service_number="SYN-4091",
        name="Ct/GD Arjun Rathore",
        phone="SYN-PHONE-4091",
        posting="Charlie company synthetic post",
        provider=provider,
    )
    assert encrypted.token == "st_364aifljnxnxpqzk"
    decrypted = await decrypt_identity(
        token=encrypted.token,
        service_no_enc=encrypted.service_no_enc,
        name_enc=encrypted.name_enc,
        phone_enc=encrypted.phone_enc,
        posting_enc=encrypted.posting_enc,
        dek_wrapped=encrypted.dek_wrapped,
        kek_version=encrypted.kek_version,
        provider=provider,
    )
    assert decrypted.service_no == "SYN-4091"
    assert decrypted.name == "Ct/GD Arjun Rathore"
    assert decrypted.phone == "SYN-PHONE-4091"


async def test_resolve_rate_limit_is_five_per_actor_per_hour() -> None:
    limiter = InMemoryResolveRateLimiter(limit=5, window_seconds=3600, clock=lambda: 1000.0)
    actor = "uwo-sunita"
    for _ in range(5):
        assert await limiter.allow(actor) is True
    assert await limiter.allow(actor) is False
    assert await limiter.allow("counsellor-anjali") is True


def test_grant_requires_purpose_bound_claims() -> None:
    settings = local_settings()
    private_key = (ROOT / "infra/keys/grant-private.pem").read_text(encoding="utf-8")
    now = datetime.now(UTC)
    encoded = jwt.encode(
        {
            "iss": settings.grant_issuer,
            "aud": settings.grant_audience,
            "sub": "st_364aifljnxnxpqzk",
            "token": "st_364aifljnxnxpqzk",
            "case_id": "MB-4091",
            "actor": "uwo-sunita",
            "actor_role": "uwo",
            "scope_path": "force.central.c02",
            "purpose_code": "welfare_contact",
            "contact_note_due_at": int((now + timedelta(hours=24)).timestamp()),
            "iat": now,
            "exp": now + timedelta(days=14),
            "jti": "grant-test-1",
        },
        private_key,
        algorithm="EdDSA",
    )
    claims = verify_grant(encoded, settings)
    assert claims.token == claims.sub
    assert claims.case_id == "MB-4091"

    with pytest.raises(ApiError) as error:
        verify_grant("not-a-grant", settings)
    assert error.value.status_code == 403
    assert error.value.code == "grant_invalid"
