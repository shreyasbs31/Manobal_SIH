"""Test settings for the identity enclave."""

from __future__ import annotations

import os

os.environ.setdefault("MANOBAL_IDENTITY_LOG_LEVEL", "WARNING")

from manobal_identity.settings.local import *  # noqa: F403

DEBUG = False
ALLOWED_HOSTS = ["testserver", "127.0.0.1", "localhost"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
