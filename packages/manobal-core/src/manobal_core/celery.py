"""Celery app for Zone 2 background work.

Nightly scoring, T4 escalation and erasure resume are scheduled here. The
broker is RabbitMQ in compose; tests run the same tasks eagerly so a missing
broker cannot hide a logic bug.
"""

from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "manobal_core.settings.local")

app = Celery("manobal_core")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(["manobal_core"])

app.conf.beat_schedule = {
    "nightly-hrms-pull": {
        "task": "manobal_core.tasks.pull_nightly_hrms",
        "schedule": crontab(hour=1, minute=30),
    },
    "nightly-score": {
        "task": "manobal_core.tasks.score_all_subjects",
        "schedule": crontab(hour=2, minute=0),
    },
    "escalate-unacked-t4": {
        "task": "manobal_core.tasks.escalate_unacked_t4",
        "schedule": crontab(minute="*/5"),
    },
    "resurface-sla-breaches": {
        "task": "manobal_core.tasks.resurface_sla_breaches",
        "schedule": crontab(minute="*/15"),
    },
    "resume-erasures": {
        "task": "manobal_core.tasks.resume_pending_erasures",
        "schedule": crontab(minute="*/10"),
    },
    "purge-separated": {
        "task": "manobal_core.tasks.purge_separated",
        "schedule": crontab(hour=3, minute=10),
    },
    "purge-raw-retention": {
        "task": "manobal_core.tasks.purge_raw_retention",
        "schedule": crontab(hour=3, minute=40),
    },
}
