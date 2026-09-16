from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[4]
RULESET_DIR = REPO_ROOT / "infra" / "rulesets"
DEV_KEYS = Path(__file__).resolve().parent / "dev_keys"


class DomainRule(BaseModel):
    weight: float
    threshold: float
    cusum_k: float
    cusum_h: float
    consent: str = "hr_derived"


class Ruleset(BaseModel):
    version: str
    status: str
    baseline: dict[str, float]
    domains: dict[str, DomainRule]
    tiers: dict[str, float]
    minimum_corroborating_domains: int
    hysteresis_cycles: int
    k_anonymity: int
    slas: dict[str, float]
    jitai: dict[str, int]
    floors: dict[str, float] = Field(default_factory=dict)
    acute: dict[str, object] = Field(default_factory=dict)
    yaml_text: str = ""
    signature: bytes = b""
    signers: list[str] = Field(default_factory=list)


def _key_path(stem: str, public: bool) -> Path:
    suffix = ".pub" if public else ".pem"
    return DEV_KEYS / f"{stem}{suffix}"


def load_private(stem: str) -> Ed25519PrivateKey:
    data = _key_path(stem, public=False).read_bytes()
    key = load_pem_private_key(data, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise TypeError("WDEC key must be Ed25519")
    return key


def load_public(stem: str) -> Ed25519PublicKey:
    data = _key_path(stem, public=True).read_bytes()
    key = load_pem_public_key(data)
    if not isinstance(key, Ed25519PublicKey):
        raise TypeError("WDEC public key must be Ed25519")
    return key


def sign_yaml(yaml_text: str, signers: tuple[str, str] = ("wdec1", "wdec2")) -> bytes:
    payload = yaml_text.encode("utf-8")
    parts = [load_private(name).sign(payload) for name in signers]
    return parts[0] + parts[1]


def verify_yaml(
    yaml_text: str,
    signature: bytes,
    signers: tuple[str, str] = ("wdec1", "wdec2"),
) -> bool:
    if len(signature) != 128:
        return False
    payload = yaml_text.encode("utf-8")
    try:
        load_public(signers[0]).verify(signature[:64], payload)
        load_public(signers[1]).verify(signature[64:], payload)
    except Exception:
        return False
    return True


def parse_ruleset(
    yaml_text: str, *, signature: bytes = b"", signers: list[str] | None = None
) -> Ruleset:
    raw: dict[str, Any] = yaml.safe_load(yaml_text)
    domains = {name: DomainRule.model_validate(body) for name, body in raw["domains"].items()}
    return Ruleset(
        version=str(raw["version"]),
        status=str(raw.get("status", "draft")),
        baseline={str(k): float(v) for k, v in raw["baseline"].items()},
        domains=domains,
        tiers={str(k): float(v) for k, v in raw["tiers"].items()},
        minimum_corroborating_domains=int(raw["minimum_corroborating_domains"]),
        hysteresis_cycles=int(raw["hysteresis_cycles"]),
        k_anonymity=int(raw["k_anonymity"]),
        slas={str(k): float(v) for k, v in raw["slas"].items()},
        jitai={str(k): int(v) for k, v in raw["jitai"].items()},
        floors={str(k): float(v) for k, v in raw.get("floors", {}).items()},
        acute=dict(raw.get("acute") or {}),
        yaml_text=yaml_text,
        signature=signature,
        signers=signers or ["wdec1", "wdec2"],
    )


def load_ruleset(version: str = "v1.0.0") -> Ruleset:
    path = RULESET_DIR / f"{version}.yaml"
    text = path.read_text(encoding="utf-8")
    signature = sign_yaml(text)
    if not verify_yaml(text, signature):
        raise RuntimeError("Ruleset signature verification failed")
    parsed = parse_ruleset(text, signature=signature, signers=["wdec1", "wdec2"])
    return parsed
