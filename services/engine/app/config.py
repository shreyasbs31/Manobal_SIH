from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    manobal_mode: Literal["demo", "sovereign"] = "demo"
    web_origin: str = "http://localhost:3000"
    core_database_url: str = (
        "postgresql+asyncpg://core_app:core_app_dev_only@localhost:5432/manobal_core"
    )
    redis_url: str = "redis://localhost:6379/0"
    vault_api_url: str = "http://localhost:8100"
    realtime_url: str = "ws://localhost:8080"
    sim_time_compression: float = Field(default=60.0, gt=0)
    realtime_jwt_secret: SecretStr = SecretStr("realtime_dev_only_change_me_32bx")
    incident_hmac_secret: SecretStr = SecretStr("incident_dev_only_change_me")
    webpubsub_connection_string: str = ""

    access_jwt_secret: SecretStr = SecretStr("access_dev_only_change_me_32bytes")
    access_token_minutes: int = Field(default=15, ge=1, le=60)
    grant_private_key_file: Path = Path("infra/keys/grant-private.pem")
    grant_issuer: str = "manobal-engine"
    grant_audience: str = "manobal-vault"

    passkey_rp_id: str = "localhost"
    passkey_rp_name: str = "MANOBAL"
    passkey_origin: str = "http://localhost:3000"
    passkey_challenge_ttl_seconds: int = Field(default=300, ge=60, le=600)

    entra_role_map: dict[str, str] = {
        "MANOBAL.Personnel": "personnel",
        "MANOBAL.Welfare": "uwo",
        "MANOBAL.Counsellor": "counsellor",
        "MANOBAL.Medical": "mo",
        "MANOBAL.Command": "commander",
        "MANOBAL.HQ": "hq",
        "MANOBAL.WDEC": "wdec",
        "MANOBAL.DPO": "dpo",
        "MANOBAL.Integrations": "hrms_integrator",
        "MANOBAL.Admin": "admin",
        "MANOBAL.Director": "director",
    }

    blob_endpoint: str = "http://127.0.0.1:10000/devstoreaccount1"
    blob_account_name: str = "devstoreaccount1"
    blob_account_key: SecretStr = SecretStr(
        "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw=="
    )
    blob_container: str = "audit-anchors"


@lru_cache
def get_settings() -> Settings:
    return Settings()
