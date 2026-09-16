from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import text

from .audit import AuditVerification, verify_audit
from .database import engine, session_factory

REQUIRED_EXTENSIONS = frozenset({"timescaledb", "vector", "ltree", "pgcrypto", "uuid-ossp"})
FORBIDDEN_IDENTITY_ENV = frozenset(
    {
        "VAULT_DATABASE_URL",
        "VAULT_DB_HOST",
        "VAULT_DB_NAME",
        "LOCAL_KEY_FILE",
        "KEYVAULT_URI",
        "KV_KEK_NAME",
        "KV_TOKEN_KEY_NAME",
    }
)
FORBIDDEN_ZONE_X_TERMS = (
    "APPRAISAL",
    "PROMOTION",
    "DISCIPLINARY",
    "MEDICAL_CATEGORY",
    "POSTING_DECISION",
)


class SelfTestReport(BaseModel):
    healthy: bool
    checked_at: datetime
    core_database_reachable: bool
    required_extensions: dict[str, bool]
    vault_database_isolated: bool
    vault_identity_keys_isolated: bool
    forbidden_identity_settings: list[str]
    audit_chain: AuditVerification
    zone_x_unreachable: bool


async def _tcp_reachable(host: str, port: int) -> bool:
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=0.75,
        )
        del reader
        writer.close()
        await writer.wait_closed()
        return True
    except (TimeoutError, OSError):
        return False


async def run_selftest() -> SelfTestReport:
    core_reachable = False
    installed: set[str] = set()
    try:
        async with engine.connect() as connection:
            core_reachable = bool(await connection.scalar(text("SELECT true")))
            result = await connection.execute(
                text(
                    """
                    SELECT extname
                      FROM pg_extension
                     WHERE extname IN (
                        'timescaledb', 'vector', 'ltree', 'pgcrypto', 'uuid-ossp'
                     )
                    """
                )
            )
            installed = {str(name) for name in result.scalars()}
    except Exception:
        core_reachable = False

    try:
        async with session_factory() as session:
            audit_result = await verify_audit(session)
    except Exception:
        audit_result = AuditVerification(
            valid=False,
            checked=0,
            broken_seq=None,
            head_hash="",
        )

    present_identity_settings = sorted(
        name for name in FORBIDDEN_IDENTITY_ENV if os.environ.get(name)
    )
    known_identity_key_paths = (
        Path("/run/manobal/dev-vault-keys.json"),
        Path("/run/manobal/vault-kek.pem"),
        Path("/run/manobal/token-hmac.key"),
    )
    identity_keys_isolated = not present_identity_settings and not any(
        path.exists() for path in known_identity_key_paths
    )
    vault_db_isolated = not await _tcp_reachable("vault-db", 5432)
    zone_x_unreachable = not any(
        any(term in name.upper() for term in FORBIDDEN_ZONE_X_TERMS)
        for name, value in os.environ.items()
        if value
    )
    extension_status = {name: name in installed for name in sorted(REQUIRED_EXTENSIONS)}
    healthy = all(
        (
            core_reachable,
            all(extension_status.values()),
            vault_db_isolated,
            identity_keys_isolated,
            audit_result.valid,
            zone_x_unreachable,
        )
    )
    return SelfTestReport(
        healthy=healthy,
        checked_at=datetime.now(UTC),
        core_database_reachable=core_reachable,
        required_extensions=extension_status,
        vault_database_isolated=vault_db_isolated,
        vault_identity_keys_isolated=identity_keys_isolated,
        forbidden_identity_settings=present_identity_settings,
        audit_chain=audit_result,
        zone_x_unreachable=zone_x_unreachable,
    )
