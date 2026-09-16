from __future__ import annotations

import asyncio
import json
import sys
from contextlib import suppress
from datetime import UTC, date, datetime

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob.aio import BlobServiceClient
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings, get_settings
from .database import session_factory


class AuditVerification(BaseModel):
    valid: bool
    checked: int
    broken_seq: int | None
    head_hash: str


class AuditAnchor(BaseModel):
    date: date
    head_hash: str
    checked: int
    created_at: datetime
    blob_uri: str | None = None


async def append_audit(
    session: AsyncSession,
    *,
    actor: str,
    action: str,
    object_ref: str,
    meta: dict[str, object] | None = None,
    sim_at: datetime | None = None,
) -> str:
    result = await session.execute(
        text(
            """
            SELECT hash
              FROM append_audit(
                :actor,
                :action,
                :object_ref,
                CAST(:meta AS jsonb),
                clock_timestamp(),
                :sim_at
              )
            """
        ),
        {
            "actor": actor,
            "action": action,
            "object_ref": object_ref,
            "meta": json.dumps(meta or {}, sort_keys=True, separators=(",", ":")),
            "sim_at": sim_at or datetime.now(UTC),
        },
    )
    await session.commit()
    return str(result.scalar_one())


async def verify_audit(session: AsyncSession) -> AuditVerification:
    row = (await session.execute(text("SELECT * FROM verify_audit_chain()"))).mappings().one()
    return AuditVerification(
        valid=bool(row["valid"]),
        checked=int(row["checked"]),
        broken_seq=(int(row["broken_seq"]) if row["broken_seq"] is not None else None),
        head_hash=str(row["head_hash"]),
    )


async def write_daily_anchor(
    settings: Settings | None = None,
) -> AuditAnchor:
    active_settings = settings or get_settings()
    async with session_factory() as session:
        verification = await verify_audit(session)
    if not verification.valid:
        raise RuntimeError("Audit chain verification failed")

    now = datetime.now(UTC)
    anchor = AuditAnchor(
        date=now.date(),
        head_hash=verification.head_hash,
        checked=verification.checked,
        created_at=now,
    )
    service = BlobServiceClient(
        account_url=active_settings.blob_endpoint,
        credential=active_settings.blob_account_key.get_secret_value(),
    )
    try:
        container = service.get_container_client(active_settings.blob_container)
        with suppress(ResourceExistsError):
            await container.create_container()
        blob = container.get_blob_client(f"{anchor.date.isoformat()}.json")
        payload = anchor.model_dump_json(exclude={"blob_uri"})
        try:
            await blob.upload_blob(payload, overwrite=False)
        except ResourceExistsError as error:
            existing = await blob.download_blob()
            if (await existing.readall()).decode("utf-8") != payload:
                raise RuntimeError(
                    "Daily audit anchor already exists with different data"
                ) from error
        return anchor.model_copy(update={"blob_uri": blob.url})
    finally:
        await service.close()


async def _main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "anchor":
        anchor = await write_daily_anchor()
        print(anchor.model_dump_json())
        return 0
    print("Usage: python -m app.audit anchor", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
