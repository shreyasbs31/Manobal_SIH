"""Subject tokens and the blind index (SDD §4.9, §5.1, FR-2.4).

Two separate mechanisms are under test, and the distinction between them is the
whole design:

*   The **subject token** is what the analytics plane sees. It is drawn from a
    CSPRNG and has no computable relationship to the service number. Nobody who
    holds a token and unlimited compute can work backwards to a person.
*   The **blind index** is what lets the vault find a row by service number
    without decrypting anything. It is deterministic, so it must never leave
    Zone 3 — its determinism is exactly what would make it a correlation key.
"""

from __future__ import annotations

import pytest

from manobal_identity.crypto.blind_index import blind_index, normalise_service_no
from manobal_identity.crypto.kms import LocalKeyManagementService
from manobal_identity.crypto.tokens import SUBJECT_TOKEN_PREFIX, mint_subject_token

SERVICE_NO = "CRPF-1987-114523"


@pytest.fixture
def kms() -> LocalKeyManagementService:
    return LocalKeyManagementService(
        keks={1: b"\x11" * 32}, active_version=1, index_key=b"\x22" * 32
    )


class TestSubjectToken:
    def test_a_token_is_unpredictable(self) -> None:
        assert len({mint_subject_token() for _ in range(2000)}) == 2000

    def test_a_token_carries_at_least_256_bits_of_entropy(self) -> None:
        """FR-2.4: guessing a valid token must not be a viable attack."""
        body = mint_subject_token().removeprefix(SUBJECT_TOKEN_PREFIX)
        assert len(body) * 5 >= 256  # base32 encodes 5 bits per character

    def test_a_token_is_prefixed_so_it_is_recognisable_in_logs_and_dumps(self) -> None:
        assert mint_subject_token().startswith(SUBJECT_TOKEN_PREFIX)

    def test_a_token_is_lowercase_and_url_safe(self) -> None:
        token = mint_subject_token()
        assert token == token.lower()
        assert token.isascii() and token.replace("_", "").isalnum()

    def test_a_token_is_not_derived_from_anything(self) -> None:
        """mint_subject_token takes no input; there is nothing to derive it from.

        This is enforced by the signature rather than by observation, because a
        statistical test cannot distinguish a good keyed hash from randomness.
        """
        import inspect

        assert inspect.signature(mint_subject_token).parameters == {}


class TestNormalisation:
    @pytest.mark.parametrize(
        "written",
        [
            "CRPF-1987-114523",
            "crpf-1987-114523",
            "  CRPF-1987-114523  ",
            "CRPF 1987 114523",
            "crpf/1987/114523",
        ],
    )
    def test_the_same_service_number_written_differently_normalises_the_same(
        self, written: str
    ) -> None:
        """HRMS extracts are not typographically consistent across forces.

        Without this, one person would acquire several tokens and their baseline
        would never accumulate.
        """
        assert normalise_service_no(written) == normalise_service_no(SERVICE_NO)

    def test_genuinely_different_service_numbers_stay_different(self) -> None:
        assert normalise_service_no("CRPF-1987-114523") != normalise_service_no(
            "CRPF-1987-114524"
        )

    def test_an_empty_service_number_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            normalise_service_no("   -- //  ")


class TestBlindIndex:
    def test_the_index_is_deterministic(
        self, kms: LocalKeyManagementService
    ) -> None:
        assert blind_index(SERVICE_NO, kms) == blind_index(SERVICE_NO, kms)

    def test_the_index_absorbs_formatting_differences(
        self, kms: LocalKeyManagementService
    ) -> None:
        assert blind_index("crpf 1987 114523", kms) == blind_index(SERVICE_NO, kms)

    def test_different_people_get_different_indexes(
        self, kms: LocalKeyManagementService
    ) -> None:
        assert blind_index("CRPF-1987-114523", kms) != blind_index(
            "CRPF-1987-114524", kms
        )

    def test_the_index_does_not_contain_the_service_number(
        self, kms: LocalKeyManagementService
    ) -> None:
        index = blind_index(SERVICE_NO, kms)
        assert SERVICE_NO.lower() not in index
        assert "114523" not in index

    def test_a_different_index_key_yields_a_different_index(self) -> None:
        """So a leaked index from one deployment cannot be replayed against another."""
        other = LocalKeyManagementService(
            keks={1: b"\x11" * 32}, active_version=1, index_key=b"\x99" * 32
        )
        default = LocalKeyManagementService(
            keks={1: b"\x11" * 32}, active_version=1, index_key=b"\x22" * 32
        )
        assert blind_index(SERVICE_NO, other) != blind_index(SERVICE_NO, default)

    def test_the_index_is_a_fixed_width_hex_digest(
        self, kms: LocalKeyManagementService
    ) -> None:
        index = blind_index(SERVICE_NO, kms)
        assert len(index) == 64
        assert all(c in "0123456789abcdef" for c in index)
