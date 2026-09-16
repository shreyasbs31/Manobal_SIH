from __future__ import annotations

from manobal_synth.persist import _stable
from manobal_synth.personas import PERSONAS


def test_eight_synthetic_personas_have_unique_tokens() -> None:
    assert len(PERSONAS) == 8
    tokens = {persona.token for persona in PERSONAS}
    case_ids = {persona.case_id for persona in PERSONAS}
    assert len(tokens) == 8
    assert len(case_ids) == 8
    for persona in PERSONAS:
        assert persona.synthetic is True
        assert persona.service_no.startswith("SYN-")
        assert persona.token.startswith("st_")
        assert len(persona.token) == 19
        assert persona.case_id.startswith("MB-")


def test_arjun_token_matches_vault_hmac() -> None:
    arjun = next(persona for persona in PERSONAS if persona.id == "arjun")
    assert arjun.token == "st_364aifljnxnxpqzk"
    assert arjun.case_id == "MB-4091"


def test_stable_ids_are_deterministic() -> None:
    assert _stable("unit:force") == _stable("unit:force")
    assert _stable("unit:force") != _stable("unit:force.central")
