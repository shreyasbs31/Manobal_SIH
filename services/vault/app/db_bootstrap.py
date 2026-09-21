from __future__ import annotations

import argparse
import os
import re

from azure.identity import DefaultAzureCredential
from azure_postgresql_auth.sqlalchemy import enable_entra_authentication
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _engine() -> tuple[Engine, DefaultAzureCredential]:
    credential = DefaultAzureCredential(
        managed_identity_client_id=os.environ.get("AZURE_CLIENT_ID") or None,
        exclude_interactive_browser_credential=True,
    )
    engine = create_engine(
        _required("DATABASE_URL"),
        connect_args={"credential": credential},
    )
    enable_entra_authentication(engine)
    return engine, credential


def _quote(connection: Connection, value: str) -> str:
    return connection.dialect.identifier_preparer.quote(value)


def create_application_principal(connection: Connection) -> None:
    identity_name = _required("APP_IDENTITY_NAME")
    identity_object_id = _required("APP_IDENTITY_OBJECT_ID")
    exists = connection.scalar(
        text("SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :name)"),
        {"name": identity_name},
    )
    if not exists:
        connection.execute(
            text(
                """
                SELECT *
                  FROM pg_catalog.pgaadauth_create_principal_with_oid(
                    :name,
                    :object_id,
                    'service',
                    false,
                    false
                  )
                """
            ),
            {"name": identity_name, "object_id": identity_object_id},
        )


def grant_application_privileges(connection: Connection) -> None:
    identity_name = _required("APP_IDENTITY_NAME")
    database_name = _required("APP_DATABASE_NAME")
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", database_name):
        raise ValueError("APP_DATABASE_NAME is invalid")
    role = _quote(connection, identity_name)
    database = _quote(connection, database_name)
    statements = (
        f"GRANT CONNECT ON DATABASE {database} TO {role}",
        f"GRANT USAGE ON SCHEMA public TO {role}",
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {role}",
        f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {role}",
        f"GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO {role}",
        (
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {role}"
        ),
        (
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            f"GRANT USAGE, SELECT ON SEQUENCES TO {role}"
        ),
        (
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            f"GRANT EXECUTE ON FUNCTIONS TO {role}"
        ),
    )
    for statement in statements:
        connection.execute(text(statement))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("principal", "grants"))
    args = parser.parse_args()
    engine, credential = _engine()
    try:
        with engine.begin() as connection:
            if args.action == "principal":
                create_application_principal(connection)
            else:
                grant_application_privileges(connection)
    finally:
        engine.dispose()
        credential.close()
    print(f"database bootstrap {args.action} complete")


if __name__ == "__main__":
    main()
