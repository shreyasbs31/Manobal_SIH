"""Test settings.

Runs against the real local PostgreSQL clusters rather than SQLite. That is not
incidental convenience — most of what this service guarantees is enforced *by*
PostgreSQL: the append-only triggers, the check constraints, the advisory lock
that serialises audit appends, and the ``pg_hba`` rejection that implements the
Zone 2/3 air-gap. A SQLite test run would pass while every one of those controls
was absent, which is the worst possible outcome for a test suite whose job is to
prove they are present.
"""

from __future__ import annotations

import os

os.environ.setdefault("MANOBAL_RULESET_REQUIRE_SIGNATURE", "false")
# Quiet by default; a failing test prints its own captured log.
os.environ.setdefault("MANOBAL_LOG_LEVEL", "WARNING")

from .local import *  # noqa: F403

DEBUG = False

# Password hashing dominates test runtime otherwise, and no test asserts
# anything about hash strength — MANOBAL never stores a password in the first
# place, since authentication belongs to the force identity provider.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Tasks run inline so a test can assert on the outcome without a broker.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Suite volume would trip the unauthenticated IP ceiling; a dedicated test
# turns the limiter back on.
RATE_LIMITS_DISABLED = True
