"""Log redaction (SDD §10.1).

The scenario these tests defend against is not a sophisticated attack. It is an
engineer adding a debug line during an incident, that line reaching a log
aggregator, and the aggregator being searchable by people who have no grant to
read anything about anyone.
"""

from __future__ import annotations

import logging

import pytest

from manobal_core.observability.redaction import REDACTED, RedactionFilter, scrub


class TestScrubbing:
    def test_a_sensitive_key_is_masked(self) -> None:
        assert scrub({"service_number": "12345678"}) == {"service_number": REDACTED}

    def test_a_benign_key_is_untouched(self) -> None:
        assert scrub({"unit_code": "12BN"}) == {"unit_code": "12BN"}

    def test_nested_structures_are_scrubbed(self) -> None:
        payload = {"outer": {"inner": {"mobile": "9876543210", "tier": "T2"}}}
        result = scrub(payload)
        assert result["outer"]["inner"]["mobile"] == REDACTED
        assert result["outer"]["inner"]["tier"] == "T2"

    def test_lists_of_records_are_scrubbed(self) -> None:
        result = scrub([{"email": "a@b.c"}, {"email": "d@e.f"}])
        assert all(item["email"] == REDACTED for item in result)

    def test_the_engine_score_is_treated_as_sensitive(self) -> None:
        """FR-3.7 again. A log line is a way out of the risk engine, and a WSI
        printed to stdout has escaped just as surely as one in a JSON response."""
        assert scrub({"wsi": 0.82})["wsi"] == REDACTED
        assert scrub({"domain_scores": {"D1": 0.9}})["domain_scores"] == REDACTED

    def test_journal_content_is_never_logged(self) -> None:
        assert scrub({"journal_text": "I have been struggling"})["journal_text"] == REDACTED

    def test_inline_key_value_pairs_in_a_message_are_masked(self) -> None:
        """Catches messages that were formatted before reaching the filter."""
        assert "12345678" not in scrub("processing service_number=12345678 for unit 12BN")

    def test_an_unquoted_multi_word_value_is_fully_masked(self) -> None:
        """A surname after a space is still the value of ``full_name``.
        Stopping at whitespace left ``Kumar`` in the log."""
        scrubbed = scrub("enrolled full_name=Rajesh Kumar unit_code=12BN")
        assert "Rajesh" not in scrubbed
        assert "Kumar" not in scrubbed
        assert "12BN" in scrubbed

    def test_scrubbing_does_not_mutate_the_callers_object(self) -> None:
        """A logger that altered the data it was asked to print would be a
        spectacular class of bug."""
        original = {"mobile": "9876543210"}
        scrub(original)
        assert original["mobile"] == "9876543210"

    def test_an_unrecognised_object_is_summarised_rather_than_repred(self) -> None:
        """A model instance's repr will happily print every field it holds."""

        class Record:
            def __init__(self) -> None:
                self.service_number = "12345678"

        assert scrub(Record()) == "<Record>"

    def test_deeply_nested_input_terminates(self) -> None:
        payload: dict[str, object] = {"k": "v"}
        for _ in range(50):
            payload = {"k": payload}
        assert scrub(payload) is not None

    @pytest.mark.parametrize("value", [1, 1.5, True, None, "plain"])
    def test_scalars_pass_through(self, value: object) -> None:
        assert scrub(value) == value


class TestFilterIntegration:
    def test_the_filter_scrubs_a_records_arguments(self) -> None:
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="scoring %s",
            args=({"service_number": "12345678", "tier": "T2"},),
            exc_info=None,
        )
        RedactionFilter().filter(record)
        assert "12345678" not in record.getMessage()
        assert "T2" in record.getMessage()

    def test_the_filter_never_drops_a_record(self) -> None:
        """Redaction must not cost observability. A dropped record is a missing
        audit trail, which is a worse failure than a masked field."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="hello",
            args=None,
            exc_info=None,
        )
        assert RedactionFilter().filter(record) is True
