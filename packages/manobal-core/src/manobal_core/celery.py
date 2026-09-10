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
    "nightly-score": {
        "task": "manobal_core.tasks.score_all_subjects",
        "schedule": crontab(hour=2, minute=15),
    },
    "escalate-unacked-t4": {
        "task": "manobal_core.tasks.escalate_unacked_t4",
        "schedule": crontab(minute="*/5"),
    },
    "resume-erasures": {
        "task": "manobal_core.tasks.resume_pending_erasures",
        "schedule": crontab(minute="*/10"),
    },
    "purge-separated": {
        "task": "manobal_core.tasks.purge_separated",
        "schedule": crontab(hour=3, minute=10),
    },
}
