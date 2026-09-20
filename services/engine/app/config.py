from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILES: list[str] = []
if os.environ.get("MANOBAL_SKIP_SECRETS") != "1":
    _ENV_FILES.append("infra/secrets.env")
_ENV_FILES.extend([".env", "infra/.env"])


def live_providers_enabled() -> bool:
    return os.environ.get("MANOBAL_FORCE_LOCAL_PROVIDERS") != "1"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=tuple(_ENV_FILES),
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
    access_token_minutes: int = Field(default=15, ge=1, le=1440)
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

    foundry_endpoint: str = ""
    ai_deployment_main: str = "main"
    ai_deployment_fast: str = "fast"
    ai_deployment_open: str = "open"
    ai_deployment_embed: str = "embed"
    ai_deployment_embed_ml: str = ""
    ai_deployment_rerank: str = ""
    ai_deployment_judge: str = ""
    ai_deployment_image: str = ""
    ai_deployment_stt_fallback: str = ""
    ai_deployment_alt: str = ""
    xai_api_key: SecretStr = SecretStr("")
    sovereign_llm_base_url: str = ""
    foundry_ad_token_file: Path | None = None
    content_safety_endpoint: str = ""
    content_safety_key: SecretStr = SecretStr("")
    translator_endpoint: str = ""
    translator_region: str = ""
    translator_key: SecretStr = SecretStr("")
    speech_region: str = ""
    speech_endpoint: str = ""
    speech_key: SecretStr = SecretStr("")
    deepgram_api_key: SecretStr = SecretStr("")
    dg_stt_model_en: str = "nova-3"
    dg_stt_model_hi: str = "nova-3"
    dg_tts_voice_en: str = "hi-IN-SwaraNeural"
    az_tts_voice_hi: str = "hi-IN-SwaraNeural"
    az_tts_voice_hinglish: str = "hi-IN-SwaraNeural"
    az_tts_voice_map: dict[str, str] = Field(
        default_factory=lambda: {
            "en": "hi-IN-SwaraNeural",
            "en-IN": "en-IN-NeerjaNeural",
            "hi": "hi-IN-SwaraNeural",
            "hi-Latn": "hi-IN-SwaraNeural",
            "ta": "ta-IN-PallaviNeural",
        }
    )
    resilience_mode: bool = False

    openai_api_key: SecretStr = SecretStr("")
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    openai_companion_fallback: bool = False
    azure_openai_api_key: SecretStr = SecretStr("")
    azure_openai_endpoint: str = ""
    azure_openai_deployment: str = ""
    azure_openai_api_version: str = "2024-10-21"
    acs_connection_string: SecretStr = SecretStr("")
    acs_endpoint: str = ""
    unit_sms_number: str = "+910000000000"
    manobal_require_live_providers: bool = False

    def missing_live_provider_names(self) -> list[str]:
        names: list[str] = []
        checks: list[tuple[str, str]] = [
            ("FOUNDRY_ENDPOINT", self.foundry_endpoint),
            ("AI_DEPLOYMENT_MAIN", self.ai_deployment_main),
            ("AI_DEPLOYMENT_FAST", self.ai_deployment_fast),
            ("AI_DEPLOYMENT_OPEN", self.ai_deployment_open),
            ("AI_DEPLOYMENT_EMBED", self.ai_deployment_embed),
            ("DEEPGRAM_API_KEY", self.deepgram_api_key.get_secret_value()),
            ("SPEECH_REGION", self.speech_region),
            ("SPEECH_KEY", self.speech_key.get_secret_value()),
            ("TRANSLATOR_KEY", self.translator_key.get_secret_value()),
            ("CONTENT_SAFETY_ENDPOINT", self.content_safety_endpoint),
            ("ACS_CONNECTION_STRING", self.acs_connection_string.get_secret_value()),
        ]
        for name, value in checks:
            if not str(value).strip():
                names.append(name)
        return names


@lru_cache
def get_settings() -> Settings:
    return Settings()
