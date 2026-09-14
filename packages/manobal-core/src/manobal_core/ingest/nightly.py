"""Pull a nightly HRMS extract when a live source is configured (FR-2.1)."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

from manobal_core.ingest.identity import get_identity
from manobal_core.ingest.pipeline import ingest_hrms_batch

logger = logging.getLogger(__name__)


def pull_nightly_hrms() -> int | None:
    """Fetch one extract over HTTPS and ingest it.

    Returns accepted rows, or ``None`` when no source is configured. A missing
    URL is the local default; it is not an error.
    """
    url = os.environ.get("MANOBAL_HRMS_URL", "").strip()
    if not url:
        return None
    if not url.startswith("https://"):
        logger.warning("hrms_pull_skipped_insecure")
        return None
    token = os.environ.get("MANOBAL_HRMS_TOKEN", "").strip()
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers, method="GET")  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            raw = response.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        logger.exception("hrms_pull_failed")
        return None
    try:
        payload = json.loads(raw.decode())
    except (UnicodeDecodeError, json.JSONDecodeError):
        logger.warning("hrms_pull_not_json")
        return None
    if not isinstance(payload, dict):
        return None
    records = payload.get("records")
    if not isinstance(records, list):
        return None
    batch = ingest_hrms_batch(
        source_system=str(payload.get("source_system") or "hrms"),
        contract_version=str(payload.get("contract_version") or "hrms-1.0"),
        records=[row for row in records if isinstance(row, dict)],
        identity=get_identity(),
    )
    return int(batch.accepted_count)
