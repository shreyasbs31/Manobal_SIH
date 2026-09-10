"""Production must not mint tokens or serve /dev/*."""

from __future__ import annotations

from importlib import reload

from django.test import Client, override_settings
from django.urls import clear_url_caches


def test_production_disables_the_local_issuer() -> None:
    from manobal_core.settings import production

    assert production.DEBUG is False
    assert production.LOCAL_ISSUER_ENABLED is False


def test_dev_token_is_unmounted_when_the_issuer_is_disabled() -> None:
    import manobal_core.urls as urls

    try:
        with override_settings(LOCAL_ISSUER_ENABLED=False):
            reload(urls)
            clear_url_caches()
            response = Client().post("/dev/token", {}, content_type="application/json")
        assert response.status_code == 404
    finally:
        reload(urls)
        clear_url_caches()
