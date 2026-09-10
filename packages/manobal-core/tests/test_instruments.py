"""Validated instruments persist a total. Item answers do not leave the scorer."""

from __future__ import annotations

import pytest

from manobal_core.apps.governance.enums import DataType
from manobal_core.apps.governance.models import ConsentEntry, ConsentTextVersion, Subject
from manobal_core.apps.psystore.models import AcuteSignal, InstrumentResponse
from manobal_core.instruments.catalogue import catalogue_payload
from manobal_core.instruments.scoring import score_answers
from manobal_core.instruments.submit import InstrumentRefused, submit_instrument

from .test_core_api import client_for, personnel_of

PHQ9_ZERO = [0, 0, 0, 0, 0, 0, 0, 0, 0]
PSS10_ALL_FOUR = [4, 4, 4, 4, 4, 4, 4, 4, 4, 4]


class TestScoring:
    def test_pss10_reverses_the_published_items(self) -> None:
        scored = score_answers("pss10", PSS10_ALL_FOUR)
        # Items 4, 5, 7, 8 (1-based) reverse from 4 to 0; the other six stay 4.
        assert scored.total == 24.0
        assert scored.acute is False

    def test_phq9_item_nine_is_acute_when_non_zero(self) -> None:
        answers = list(PHQ9_ZERO)
        answers[8] = 2
        scored = score_answers("phq9", answers)
        assert scored.acute is True
        assert scored.acute_item_code == "phq9_item9_positive"
        assert scored.total == 2.0

    def test_an_implausibly_fast_completion_is_straight_lined(self) -> None:
        scored = score_answers("phq9", PHQ9_ZERO, duration_seconds=5)
        assert scored.straight_lined is True


@pytest.mark.django_db(databases=["default", "psy"])
class TestSubmission:
    def test_self_report_consent_is_required(
        self, subject: Subject, consent_text: ConsentTextVersion
    ) -> None:
        del consent_text
        with pytest.raises(InstrumentRefused, match="consent"):
            submit_instrument(subject, code="phq9", language="en", answers=PHQ9_ZERO)

    def test_item_answers_are_not_persisted(
        self, subject: Subject, consent_text: ConsentTextVersion
    ) -> None:
        ConsentEntry.objects.create(
            subject_token=subject.subject_token,
            data_type=DataType.SELF_REPORT,
            granted=True,
            consent_text=consent_text,
        )
        answers = [1, 0, 2, 1, 0, 3, 1, 0, 0]
        submit_instrument(subject, code="phq9", language="en", answers=answers)
        row = InstrumentResponse.objects.get(subject_token=subject.subject_token)
        names = {field.name for field in row._meta.get_fields()}
        assert "answers" not in names
        assert "items" not in names
        assert row.subscales == {}
        assert row.total_score == 8.0
        dumped = str(row.__dict__)
        assert str(answers) not in dumped

    def test_phq9_item_nine_raises_acute(
        self, subject: Subject, officer, consent_text: ConsentTextVersion
    ) -> None:
        del officer
        ConsentEntry.objects.create(
            subject_token=subject.subject_token,
            data_type=DataType.SELF_REPORT,
            granted=True,
            consent_text=consent_text,
        )
        answers = list(PHQ9_ZERO)
        answers[8] = 1
        submit_instrument(subject, code="phq9", language="en", answers=answers)
        signal = AcuteSignal.objects.get(subject_token=subject.subject_token)
        assert signal.signal_code == "phq9_item9_positive"
        assert signal.source == "instrument"


@pytest.mark.django_db(databases=["default", "psy"])
class TestInstrumentHttp:
    def test_the_catalogue_is_available_in_english_and_hindi(
        self, subject: Subject, consent_text: ConsentTextVersion
    ) -> None:
        del consent_text
        client = client_for(personnel_of(subject))
        english = client.get("/v1/me/instruments/catalogue", {"code": "phq9", "lang": "en"})
        hindi = client.get("/v1/me/instruments/catalogue", {"code": "phq9", "lang": "hi"})
        assert english.status_code == 200
        assert hindi.status_code == 200
        assert english.json()["items"][8].startswith("Thoughts that you would be better off dead")
        assert "मर जाएँ" in hindi.json()["items"][8]
        assert "score" not in english.json()
        assert "total" not in english.json()

    def test_an_officer_cannot_read_the_catalogue(
        self, subject: Subject, officer_principal
    ) -> None:
        del subject
        response = client_for(officer_principal).get("/v1/me/instruments/catalogue")
        assert response.status_code == 403

    def test_submit_without_consent_is_refused(
        self, subject: Subject, consent_text: ConsentTextVersion
    ) -> None:
        del consent_text
        response = client_for(personnel_of(subject)).post(
            "/v1/me/instruments",
            {"code": "phq9", "language": "en", "answers": PHQ9_ZERO},
            format="json",
        )
        assert response.status_code == 422
        assert response.json()["code"] == "MB-4220"

    def test_submit_returns_a_total_and_never_the_answers(
        self, subject: Subject, consent_text: ConsentTextVersion
    ) -> None:
        ConsentEntry.objects.create(
            subject_token=subject.subject_token,
            data_type=DataType.SELF_REPORT,
            granted=True,
            consent_text=consent_text,
        )
        response = client_for(personnel_of(subject)).post(
            "/v1/me/instruments",
            {"code": "gad7", "language": "en", "answers": [1, 1, 1, 1, 1, 1, 1]},
            format="json",
        )
        assert response.status_code == 201
        body = response.json()
        assert body["total"] == 7.0
        assert "answers" not in body
        assert catalogue_payload("gad7", "en")["items"][0] not in response.content.decode()
