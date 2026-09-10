"""Production settings. The local issuer and /dev/* routes do not exist here."""

from __future__ import annotations

import os

os.environ.setdefault("MANOBAL_ENV", "prod")
os.environ.setdefault("MANOBAL_RULESET_REQUIRE_SIGNATURE", "true")

from .base import *  # noqa: F403
from .base import JOURNAL, ImproperlyConfigured

DEBUG = False
LOCAL_ISSUER_ENABLED = False

if not str(JOURNAL.get("MASTER_KEY_B64") or ""):
    raise ImproperlyConfigured(
        "MANOBAL_JOURNAL_MASTER_KEY must be set in production. "
        "A missing journal key would store ciphertext that can never be erased."
    )
