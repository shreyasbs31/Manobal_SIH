"""Envelope encryption for the identity vault (SDD NFR-SEC2, §4.9).

The requirement these tests hold the implementation to is narrow and absolute:
a stolen database dump, on its own, must be ciphertext. Every assertion here
is a restatement of that sentence from a different angle.
"""

from __future__ import annotations

import pytest
from cryptography.exceptions import InvalidTag

from manobal_identity.crypto.envelope import EnvelopeCipher, SealedValue
from manobal_identity.crypto.kms import (
    LocalKeyManagementService,
    UnknownKeyVersionError,
)

SERVICE_NO = "CRPF-1987-114523"
NAME = "Havildar A. Kumar"
TOKEN = "st_7ytfnvqzk4c2mjxr6d8p3lwaeh5s9bug"


@pytest.fixture
def kms() -> LocalKeyManagementService:
    return LocalKeyManagementService(
        keks={1: b"\x11" * 32},
        active_version=1,
        index_key=b"\x22" * 32,
    )


@pytest.fixture
def cipher(kms: LocalKeyManagementService) -> EnvelopeCipher:
    return EnvelopeCipher(kms)


def aad(field: str, token: str = TOKEN) -> bytes:
    return f"subject_identity|{field}|{token}".encode()


class TestRoundTrip:
    def test_a_sealed_value_opens_back_to_the_original_text(
        self, cipher: EnvelopeCipher
    ) -> None:
        key = cipher.new_record_key()
        sealed = cipher.seal(key, NAME, aad=aad("full_name"))
        assert cipher.open(key, sealed, aad=aad("full_name")) == NAME

    def test_a_record_key_survives_being_wrapped_and_unwrapped(
        self, cipher: EnvelopeCipher
    ) -> None:
        key = cipher.new_record_key()
        sealed = cipher.seal(key, SERVICE_NO, aad=aad("service_no"))

        # Simulate a fresh process: only the wrapped key came back from the database.
        reloaded = cipher.load_record_key(key.wrapped)
        assert cipher.open(reloaded, sealed, aad=aad("service_no")) == SERVICE_NO

    def test_one_record_key_protects_every_field_of_that_record(
        self, cipher: EnvelopeCipher
    ) -> None:
        key = cipher.new_record_key()
        fields = {"service_no": SERVICE_NO, "full_name": NAME, "rank_code": "HAV"}
        sealed = {f: cipher.seal(key, v, aad=aad(f)) for f, v in fields.items()}

        reloaded = cipher.load_record_key(key.wrapped)
        for field, value in fields.items():
            assert cipher.open(reloaded, sealed[field], aad=aad(field)) == value

    def test_unicode_survives_the_round_trip(self, cipher: EnvelopeCipher) -> None:
        key = cipher.new_record_key()
        name = "हवलदार अ. कुमार"
        sealed = cipher.seal(key, name, aad=aad("full_name"))
        assert cipher.open(key, sealed, aad=aad("full_name")) == name


class TestCiphertextLeaksNothing:
    def test_the_same_plaintext_seals_differently_every_time(
        self, cipher: EnvelopeCipher
    ) -> None:
        """Otherwise equal names would be visible as equal ciphertext in a dump."""
        key = cipher.new_record_key()
        first = cipher.seal(key, NAME, aad=aad("full_name"))
        second = cipher.seal(key, NAME, aad=aad("full_name"))
        assert first.ciphertext != second.ciphertext

    def test_two_records_with_the_same_name_are_not_correlatable(
        self, cipher: EnvelopeCipher
    ) -> None:
        a = cipher.seal(cipher.new_record_key(), NAME, aad=aad("full_name", "st_a"))
        b = cipher.seal(cipher.new_record_key(), NAME, aad=aad("full_name", "st_b"))
        assert a.ciphertext != b.ciphertext

    def test_the_plaintext_does_not_appear_in_the_serialised_form(
        self, cipher: EnvelopeCipher
    ) -> None:
        key = cipher.new_record_key()
        sealed = cipher.seal(key, SERVICE_NO, aad=aad("service_no"))
        assert SERVICE_NO.encode() not in bytes(sealed)
        assert SERVICE_NO.encode() not in key.wrapped

    def test_the_data_key_never_appears_in_its_wrapped_form(
        self, cipher: EnvelopeCipher
    ) -> None:
        key = cipher.new_record_key()
        assert key.data_key not in key.wrapped


class TestTamperEvidence:
    def test_flipping_a_ciphertext_bit_is_detected(
        self, cipher: EnvelopeCipher
    ) -> None:
        key = cipher.new_record_key()
        sealed = cipher.seal(key, NAME, aad=aad("full_name"))
        corrupted = SealedValue(
            nonce=sealed.nonce,
            ciphertext=bytes([sealed.ciphertext[0] ^ 0x01]) + sealed.ciphertext[1:],
        )
        with pytest.raises(InvalidTag):
            cipher.open(key, corrupted, aad=aad("full_name"))

    def test_flipping_a_nonce_bit_is_detected(self, cipher: EnvelopeCipher) -> None:
        key = cipher.new_record_key()
        sealed = cipher.seal(key, NAME, aad=aad("full_name"))
        corrupted = SealedValue(
            nonce=bytes([sealed.nonce[0] ^ 0x01]) + sealed.nonce[1:],
            ciphertext=sealed.ciphertext,
        )
        with pytest.raises(InvalidTag):
            cipher.open(key, corrupted, aad=aad("full_name"))

    def test_tampering_with_a_wrapped_key_is_detected(
        self, cipher: EnvelopeCipher
    ) -> None:
        key = cipher.new_record_key()
        blob = bytearray(key.wrapped)
        blob[-1] ^= 0x01
        with pytest.raises(InvalidTag):
            cipher.load_record_key(bytes(blob))


class TestCiphertextIsBoundToItsPlace:
    """A ciphertext moved to another column or another row must not open.

    Without this, a DBA could swap one person's name into another person's row,
    or move an encrypted mobile number into the name column, and the application
    would decrypt it happily.
    """

    def test_a_value_will_not_open_under_a_different_field_name(
        self, cipher: EnvelopeCipher
    ) -> None:
        key = cipher.new_record_key()
        sealed = cipher.seal(key, NAME, aad=aad("full_name"))
        with pytest.raises(InvalidTag):
            cipher.open(key, sealed, aad=aad("rank_code"))

    def test_a_value_will_not_open_under_a_different_subject_token(
        self, cipher: EnvelopeCipher
    ) -> None:
        key = cipher.new_record_key()
        sealed = cipher.seal(key, NAME, aad=aad("full_name", "st_original"))
        with pytest.raises(InvalidTag):
            cipher.open(key, sealed, aad=aad("full_name", "st_someone_else"))

    def test_a_value_will_not_open_under_another_records_key(
        self, cipher: EnvelopeCipher
    ) -> None:
        sealed = cipher.seal(cipher.new_record_key(), NAME, aad=aad("full_name"))
        with pytest.raises(InvalidTag):
            cipher.open(cipher.new_record_key(), sealed, aad=aad("full_name"))


class TestKeyRotation:
    """NFR-SEC2 requires 90-day rotation. Rotation must not orphan old rows."""

    def test_records_sealed_under_the_old_kek_still_open_after_rotation(self) -> None:
        old = LocalKeyManagementService(
            keks={1: b"\x11" * 32}, active_version=1, index_key=b"\x22" * 32
        )
        key = EnvelopeCipher(old).new_record_key()
        sealed = EnvelopeCipher(old).seal(key, NAME, aad=aad("full_name"))

        rotated = LocalKeyManagementService(
            keks={1: b"\x11" * 32, 2: b"\x33" * 32},
            active_version=2,
            index_key=b"\x22" * 32,
        )
        cipher = EnvelopeCipher(rotated)
        reloaded = cipher.load_record_key(key.wrapped)
        assert cipher.open(reloaded, sealed, aad=aad("full_name")) == NAME

    def test_new_records_are_sealed_under_the_new_kek(self) -> None:
        rotated = LocalKeyManagementService(
            keks={1: b"\x11" * 32, 2: b"\x33" * 32},
            active_version=2,
            index_key=b"\x22" * 32,
        )
        assert EnvelopeCipher(rotated).new_record_key().kek_version == 2

    def test_a_retired_kek_cannot_be_silently_ignored(
        self, cipher: EnvelopeCipher
    ) -> None:
        """If a KEK is withdrawn, its records must fail loudly, not decrypt wrongly."""
        key = cipher.new_record_key()
        without_v1 = LocalKeyManagementService(
            keks={2: b"\x33" * 32}, active_version=2, index_key=b"\x22" * 32
        )
        with pytest.raises(UnknownKeyVersionError):
            EnvelopeCipher(without_v1).load_record_key(key.wrapped)


class TestKeyMaterialHygiene:
    def test_a_kek_must_be_256_bits(self) -> None:
        with pytest.raises(ValueError, match="256 bits"):
            LocalKeyManagementService(
                keks={1: b"\x11" * 16}, active_version=1, index_key=b"\x22" * 32
            )

    def test_an_index_key_must_be_256_bits(self) -> None:
        with pytest.raises(ValueError, match="256 bits"):
            LocalKeyManagementService(
                keks={1: b"\x11" * 32}, active_version=1, index_key=b"\x22" * 8
            )

    def test_the_active_version_must_actually_be_held(self) -> None:
        with pytest.raises(ValueError, match="active"):
            LocalKeyManagementService(
                keks={1: b"\x11" * 32}, active_version=9, index_key=b"\x22" * 32
            )

    def test_at_least_one_kek_is_required(self) -> None:
        with pytest.raises(ValueError, match="at least one"):
            LocalKeyManagementService(
                keks={}, active_version=1, index_key=b"\x22" * 32
            )

    def test_the_kms_does_not_expose_key_material_in_its_repr(
        self, kms: LocalKeyManagementService
    ) -> None:
        """Key bytes in a traceback or a log line are a disclosure incident."""
        rendered = f"{kms!r} {kms!s}"
        assert "\\x11" not in rendered
        assert "1111" not in rendered
