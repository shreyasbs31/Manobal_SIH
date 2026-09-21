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

from .config import get_settings

settings = get_settings()
database_credential: DefaultAzureCredential | None = None

if settings.vault_database_entra_auth:
    database_credential = DefaultAzureCredential(
        managed_identity_client_id=settings.azure_client_id or None,
        exclude_interactive_browser_credential=True,
    )
    engine: AsyncEngine = create_asyncpg_engine(
        settings.vault_database_url,
        database_credential,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
    )
else:
    engine = create_async_engine(
        settings.vault_database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
    )
session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


async def vault_ping() -> bool:
    try:
        async with engine.connect() as connection:
            return bool(await connection.scalar(text("SELECT true")))
    except Exception:
        return False


async def close_database() -> None:
    await engine.dispose()
    if database_credential is not None:
        await database_credential.close()
