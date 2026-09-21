from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from azure.identity import DefaultAzureCredential
from azure_postgresql_auth.sqlalchemy import enable_entra_authentication
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = os.environ.get("VAULT_DATABASE_URL")
if database_url:
    config.set_main_option(
        "sqlalchemy.url",
        database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1),
    )

target_metadata = None


def _entra_enabled() -> bool:
    return os.environ.get("VAULT_DATABASE_ENTRA_AUTH", "").strip().lower() in {
        "1",
        "true",
    }


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    credential: DefaultAzureCredential | None = None
    connect_args: dict[str, object] = {}
    if _entra_enabled():
        credential = DefaultAzureCredential(
            managed_identity_client_id=os.environ.get("AZURE_CLIENT_ID") or None,
            exclude_interactive_browser_credential=True,
        )
        connect_args["credential"] = credential
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url") or "",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )
    if credential is not None:
        enable_entra_authentication(connectable)
    try:
        with connectable.connect() as connection:
            do_run_migrations(connection)
    finally:
        connectable.dispose()
        if credential is not None:
            credential.close()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
