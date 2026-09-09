"""Development settings for the identity enclave.

The keys below are development keys and are safe only because they are useless:
they protect a vault full of synthetic people. Production supplies real key
material through the KMS, and `base.py` refuses to start without it.
"""

from __future__ import annotations

import base64
import os

os.environ.setdefault("MANOBAL_IDENTITY_SECRET_KEY", "dev-only-not-a-secret")
os.environ.setdefault("MANOBAL_IDENTITY_DB_PASSWORD", "dev_only_not_a_secret")
os.environ.setdefault("MANOBAL_IDENTITY_DB_SSLMODE", "disable")
os.environ.setdefault("MANOBAL_IDENTITY_ALLOWED_HOSTS", "127.0.0.1,localhost")
os.environ.setdefault("MANOBAL_IDENTITY_REQUIRE_MTLS", "false")
os.environ.setdefault(
    "MANOBAL_IDENTITY_KEK_V1", base64.b64encode(b"\x11" * 32).decode()
)
os.environ.setdefault(
    "MANOBAL_IDENTITY_INDEX_KEY", base64.b64encode(b"\x22" * 32).decode()
)
# Public half of the Zone 2 local seed (private bytes 0x44 * 32, key_id core-dev).
os.environ.setdefault(
    "MANOBAL_IDENTITY_GRANT_KEYS",
    "core-dev=11l5O7wTooGagnx2rbb7qKSa7gB/SfLQmS2ZuCWtLEg=",
)

from manobal_identity.settings.base import *  # noqa: F403

DEBUG = True
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
