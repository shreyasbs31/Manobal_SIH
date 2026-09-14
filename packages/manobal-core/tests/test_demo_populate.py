"""The demo seed writes enough simulated history for every console."""

from __future__ import annotations

import pytest

from manobal_core.apps.governance.models import ConsentTextVersion, Subject, Unit
from manobal_core.apps.psystore.models import CheckinResponse
from manobal_core.demo.populate import populate_demo
from manobal_core.ingest.incidents import offer_checkin_for

pytestmark = pytest.mark.django_db(databases=["default", "org", "psy", "bio", "voice"])


def test_populate_demo_writes_checkins_and_an_incident(
    subject: Subject,
    unit_tree: dict[str, Unit],
    consent_text: ConsentTextVersion,
    officer,
) -> None:
    del officer
    from manobal_core.apps.governance.enums import DataType
    from manobal_core.apps.governance.models import ConsentEntry

    ConsentEntry.objects.create(
        subject_token=subject.subject_token,
        data_type=DataType.JOURNAL,
        granted=True,
        consent_text=consent_text,
    )
    demo = populate_demo([subject], company=unit_tree["company"], consent_text=consent_text)
    assert demo["checkins"] == 14
    assert CheckinResponse.objects.filter(subject_token=subject.subject_token).count() == 14
    offer = offer_checkin_for(subject)
    assert offer["offer_checkin"] is True
