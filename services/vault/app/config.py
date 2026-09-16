from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    manobal_mode: Literal["demo", "sovereign"] = "demo"
    vault_database_url: str = (
        "postgresql+asyncpg://vault_app:vault_app_dev_only@localhost:5432/manobal_vault"
    )
    redis_url: str = "redis://localhost:6379/1"
    key_provider: Literal["local", "azure"] = "local"
    local_key_file: Path = Path("infra/keys/dev-vault-keys.json")
    keyvault_uri: str | None = None
    kv_kek_name: str = "vault-kek"
    kv_token_key_name: str = "vault-token-hmac"
    grant_public_key_file: Path = Path("infra/keys/grant-public.pem")
    grant_issuer: str = "manobal-engine"
    grant_audience: str = "manobal-vault"
    tokenise_ingest_secret: SecretStr = SecretStr("ingest_dev_only_change_me")
    resolve_rate_limit: int = Field(default=5, ge=1, le=20)
    resolve_window_seconds: int = Field(default=3600, ge=60, le=86400)

    @model_validator(mode="after")
    def validate_key_provider(self) -> Settings:
        if self.manobal_mode != "demo" and self.key_provider == "local":
            raise ValueError("The local key provider is allowed only in demo mode")
        if self.key_provider == "azure" and not self.keyvault_uri:
            raise ValueError("KEYVAULT_URI is required for the Azure key provider")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
