from __future__ import annotations

from pathlib import Path

from pydantic import SecretStr

from app.config import Settings
from app.providers.foundry import FoundryClient, file_token_ok


def test_file_token_rejects_directory(tmp_path: Path) -> None:
    folder = tmp_path / "foundry.token"
    folder.mkdir()
    assert file_token_ok(folder) is False


def test_file_token_rejects_tiny_file(tmp_path: Path) -> None:
    path = tmp_path / "foundry.token"
    path.write_text("x", encoding="utf-8")
    assert file_token_ok(path) is False


def test_auth_path_prefers_entra_file(tmp_path: Path) -> None:
    path = tmp_path / "foundry.token"
    path.write_text("a" * 40, encoding="utf-8")
    settings = Settings.model_construct(
        foundry_endpoint="https://manobal-ai-resource.openai.azure.com/openai/v1",
        azure_openai_endpoint="https://manobal-ai-resource.openai.azure.com/openai/v1",
        foundry_ad_token_file=path,
        azure_openai_api_key=SecretStr(""),
    )
    client = FoundryClient(settings)
    assert client.auth_path() == "entra_file"


def test_auth_path_uses_key_when_file_missing() -> None:
    settings = Settings.model_construct(
        foundry_endpoint="https://manobal-ai-resource.openai.azure.com/openai/v1",
        azure_openai_endpoint="https://manobal-ai-resource.openai.azure.com/openai/v1",
        foundry_ad_token_file=None,
        azure_openai_api_key=SecretStr("not-a-real-key"),
    )
    client = FoundryClient(settings)
    assert client.auth_path() == "azure_openai_key"
