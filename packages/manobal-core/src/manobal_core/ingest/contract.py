"""The published HRMS extract contract (FR-2.3, FR-2.4).

Validation is an allow-list. Fields that identify a person are named here so
they can be dropped after tokenisation; a new identifying column that is not
on this list cannot reach ``org_store`` because it is never copied into the
stored payload.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Final

HRMS_CONTRACT: Final = "hrms-1.0"

IDENTIFYING_FIELDS: Final = frozenset(
    {
        "service_no",
        "full_name",
        "rank_code",
        "mobile_e164",
        "name",
        "first_name",
        "last_name",
        "phone",
        "email",
        "aadhaar",
    }
)

_IDENTITY_REQUIRED: Final = (
    "service_no",
    "full_name",
    "rank_code",
    "mobile_e164",
    "unit_code",
    "unit_path",
    "force_code",
    "enrolled_on",
)

_FEATURE_KEYS: Final = frozenset(
    {
        "observed_on",
        "rank_band",
        "service_years_bucket",
        "duty_hours",
        "night_duty",
        "consecutive_duty_days",
        "high_alert_posting",
        "location_changes_30d",
        "days_since_last_leave",
        "leave_denied_count_90d",
        "leave_deferred_days",
        "pending_leave_application",
        "home_distance_band",
        "unit_code",
        "unit_path",
        "force_code",
        "employment_status",
    }
)


def validate_envelope(contract_version: str) -> str | None:
    if contract_version != HRMS_CONTRACT:
        return "unknown_contract_version"
    return None


def identity_person(record: dict[str, Any]) -> dict[str, str] | None:
    """The fields Zone 3 needs to tokenise this person, or ``None`` if incomplete."""
    missing = [field for field in _IDENTITY_REQUIRED if not record.get(field)]
    if missing:
        return None
    return {field: str(record[field]) for field in _IDENTITY_REQUIRED}


def strip_identifiers(record: dict[str, Any]) -> dict[str, Any]:
    """Return only the fields the analytics plane is allowed to keep."""
    return {key: value for key, value in record.items() if key in _FEATURE_KEYS}


def validate_features(payload: dict[str, Any]) -> str | None:
    raw_day = payload.get("observed_on")
    if not raw_day:
        return "missing_observed_on"
    try:
        date.fromisoformat(str(raw_day))
    except ValueError:
        return "invalid_observed_on"
    hours = payload.get("duty_hours")
    if hours is not None:
        try:
            if float(hours) < 0 or float(hours) > 48:
                return "invalid_duty_hours"
        except (TypeError, ValueError):
            return "invalid_duty_hours"
    return None
