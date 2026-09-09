"""Test settings for the identity enclave."""

from __future__ import annotations

import os

os.environ.setdefault("MANOBAL_IDENTITY_LOG_LEVEL", "WARNING")

from manobal_identity.settings.local import *  # noqa: F403

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
