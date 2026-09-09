"""Store routing — SDD §5.1.

Six logical stores, five of which live in this service. They are *separate
databases*, not schemas, and that choice is doing real work: PostgreSQL cannot
join across databases, so "no cross-store join" stops being a rule an engineer
has to remember and becomes something the query planner will not do.

The consequence engineers feel daily is that there is no ``ForeignKey`` from a
signal record to a subject. ``subject_token`` is a plain indexed column in every
store, and joining is an explicit application-layer act. That is the same shape
SDD §5.1 mandates between ``iam_vault`` and everything else, applied one level
down — and it is why a compromise of ``bio_store`` yields heart-rate traces
belonging to nobody in particular.
"""

from __future__ import annotations

from typing import Any

from django.db.models import Model

#: Django app label -> database alias. The five aliases match the five analytics
#: databases created by packages/manobal-infra/postgres/analytics-init.sql.
STORE_BY_APP: dict[str, str] = {
    "governance": "default",  # gov_store: consent, audit, grants, cases, alerts, assessments
    "orgstore": "org",  # org_store: derived organisational indicators
    "psystore": "psy",  # psy_store: instrument scores, EMA, opt-in journal
    "biostore": "bio",  # bio_store: wearable time series (TimescaleDB)
    "voicestore": "voice",  # voice_store: eGeMAPS vectors. No audio. No transcript.
}

#: Django's own machinery lives in gov_store alongside the governance models,
#: because sessions and permissions are governance concerns.
_DJANGO_INTERNAL_APPS = frozenset(
    {"contenttypes", "auth", "sessions", "admin", "messages", "staticfiles"}
)


class StoreRouter:
    """Route each app to its own database and refuse cross-store relations."""

    def db_for_read(self, model: type[Model], **hints: Any) -> str | None:
        return STORE_BY_APP.get(model._meta.app_label)

    def db_for_write(self, model: type[Model], **hints: Any) -> str | None:
        return STORE_BY_APP.get(model._meta.app_label)

    def allow_relation(self, obj1: Model, obj2: Model, **hints: Any) -> bool | None:
        """Permit a relation only when both models live in the same store.

        Returning ``False`` rather than ``None`` matters: ``None`` means "no
        opinion" and lets Django fall through to allowing it. A cross-store
        ForeignKey is a privacy defect, so this router has an opinion.
        """
        left = STORE_BY_APP.get(obj1._meta.app_label)
        right = STORE_BY_APP.get(obj2._meta.app_label)
        if left is None or right is None:
            return None
        return left == right

    def allow_migrate(
        self,
        db: str,
        app_label: str,
        model_name: str | None = None,
        **hints: Any,
    ) -> bool | None:
        if app_label in _DJANGO_INTERNAL_APPS:
            return db == "default"
        target = STORE_BY_APP.get(app_label)
        if target is None:
            return None
        return db == target
