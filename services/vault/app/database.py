from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import get_settings

engine: AsyncEngine = create_async_engine(
    get_settings().vault_database_url,
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
