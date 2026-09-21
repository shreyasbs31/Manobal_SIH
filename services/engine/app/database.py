from __future__ import annotations

from collections.abc import AsyncIterator

from azure.identity.aio import DefaultAzureCredential
from azure_postgresql_auth.sqlalchemy import create_asyncpg_engine
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .auth import Principal
from .config import get_settings

settings = get_settings()
database_credential: DefaultAzureCredential | None = None

if settings.core_database_entra_auth:
    database_credential = DefaultAzureCredential(
        managed_identity_client_id=settings.azure_client_id or None,
        exclude_interactive_browser_credential=True,
    )
    engine: AsyncEngine = create_asyncpg_engine(
        settings.core_database_url,
        database_credential,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        connect_args={"timeout": 3, "command_timeout": 8},
    )
else:
    engine = create_async_engine(
        settings.core_database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        connect_args={"timeout": 3, "command_timeout": 8},
    )
session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


async def apply_rls_context(session: AsyncSession, principal: Principal) -> None:
    values = {
        "role": principal.role.value,
        "subject_token": principal.subject_token or "",
        "scope_path": principal.scope_path,
        "actor_id": principal.actor_id,
    }
    for key, value in values.items():
        await session.execute(
            text("SELECT set_config(:setting, :value, true)"),
            {"setting": f"app.{key}", "value": value},
        )


async def core_ping() -> bool:
    try:
        async with engine.connect() as connection:
            return bool(await connection.scalar(text("SELECT true")))
    except Exception:
        return False


async def close_database() -> None:
    await engine.dispose()
    if database_credential is not None:
        await database_credential.close()
