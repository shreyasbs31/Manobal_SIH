"""Store routing is the privacy boundary that PostgreSQL cannot express as a join.

Six logical stores, five of which this service owns. They are separate
databases, not schemas, so a forgotten ForeignKey cannot quietly reconstruct a
person from a heart-rate row. These tests pin the routing table and the
``allow_migrate`` paths that coverage had never exercised.
"""

from __future__ import annotations

from types import SimpleNamespace

from manobal_core.db.routers import STORE_BY_APP, StoreRouter

router = StoreRouter()


def _model(app_label: str) -> SimpleNamespace:
    return SimpleNamespace(_meta=SimpleNamespace(app_label=app_label))


class TestReadAndWrite:
    def test_each_app_reads_from_its_own_store(self) -> None:
        for app, alias in STORE_BY_APP.items():
            assert router.db_for_read(_model(app)) == alias
            assert router.db_for_write(_model(app)) == alias

    def test_an_unknown_app_is_left_to_django(self) -> None:
        assert router.db_for_read(_model("sessions")) is None


class TestRelations:
    def test_two_models_in_the_same_store_may_relate(self) -> None:
        assert router.allow_relation(_model("governance"), _model("governance")) is True

    def test_a_cross_store_relation_is_refused(self) -> None:
        """Returning False, not None: None means 'no opinion' and Django allows it."""
        assert router.allow_relation(_model("biostore"), _model("governance")) is False

    def test_an_unmapped_app_has_no_opinion(self) -> None:
        assert router.allow_relation(_model("auth"), _model("governance")) is None


class TestMigrations:
    def test_each_app_migrates_only_onto_its_own_store(self) -> None:
        for app, alias in STORE_BY_APP.items():
            assert router.allow_migrate(alias, app) is True
            others = {db for db in STORE_BY_APP.values() if db != alias}
            for other in others:
                assert router.allow_migrate(other, app) is False

    def test_django_internal_tables_stay_on_gov_store(self) -> None:
        for app in ("contenttypes", "auth", "sessions", "admin"):
            assert router.allow_migrate("default", app) is True
            assert router.allow_migrate("bio", app) is False

    def test_an_unknown_app_has_no_opinion(self) -> None:
        assert router.allow_migrate("default", "not_a_manobal_app") is None
