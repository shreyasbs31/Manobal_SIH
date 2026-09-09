"""Log lines emitted during a request must name the actor (§10.1).

The binding used to happen in middleware, after ``get_response`` returned. By
then the view had finished: the scoring run, the consent check and the identity
resolution had all already logged, every one of them with an empty actor. Those
are exactly the lines an auditor asks about, and the one line that did carry an
actor was the access log, which says only that a request happened.

The second half of this is teardown, and it is the part that bites in
production rather than in tests. Workers are reused. A context variable left set
by one request is inherited by the next one to land on that thread, so an
unauthenticated request logs under whoever was served just before it. An audit
trail that names the wrong officer is worse than one that names nobody.
"""

from __future__ import annotations

import pytest

from manobal_core.apps.authz.middleware import PrincipalMiddleware
from manobal_core.apps.governance.enums import Role
from manobal_core.observability.logging import (
    JsonFormatter,
    actor_id_var,
    actor_role_var,
    request_id_var,
)
from manobal_core.observability.middleware import RequestContextMiddleware


@pytest.fixture(autouse=True)
def clean_context():
    id_token = actor_id_var.set("")
    role_token = actor_role_var.set("")
    request_token = request_id_var.set("")
    yield
    actor_id_var.reset(id_token)
    actor_role_var.reset(role_token)
    request_id_var.reset(request_token)


class TestBindingHappensEarlyEnough:
    def test_the_actor_is_visible_to_code_running_inside_the_view(self) -> None:
        """The regression this module exists to prevent."""
        seen: dict[str, str] = {}

        def view(request):
            # Stand in for DRF authentication, which runs at this point.
            actor_id_var.set("officer_221")
            actor_role_var.set(Role.WELFARE_OFFICER.value)
            seen["during"] = actor_id_var.get()
            return "response"

        PrincipalMiddleware(view)(object())
        assert seen["during"] == "officer_221"


class TestTeardown:
    def test_an_actor_does_not_leak_into_the_next_request(self) -> None:
        def authenticated(request):
            actor_id_var.set("officer_221")
            return "ok"

        def anonymous(request):
            assert actor_id_var.get() == ""
            return "ok"

        middleware_a = PrincipalMiddleware(authenticated)
        middleware_b = PrincipalMiddleware(anonymous)
        middleware_a(object())
        middleware_b(object())
        assert actor_id_var.get() == ""

    def test_the_context_is_cleared_even_when_the_view_raises(self) -> None:
        """A 500 is when you most want the next request's logs to be honest."""

        def exploding(request):
            actor_id_var.set("officer_221")
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            PrincipalMiddleware(exploding)(object())
        assert actor_id_var.get() == ""

    def test_the_role_is_cleared_alongside_the_id(self) -> None:
        def view(request):
            actor_role_var.set(Role.MEDICAL_OFFICER.value)
            return "ok"

        PrincipalMiddleware(view)(object())
        assert actor_role_var.get() == ""

    def test_a_request_starts_from_an_empty_actor(self) -> None:
        """Not from whatever the enclosing context happened to hold."""
        actor_id_var.set("stale_officer")
        observed: dict[str, str] = {}

        def view(request):
            observed["at_entry"] = actor_id_var.get()
            return "ok"

        PrincipalMiddleware(view)(object())
        assert observed["at_entry"] == ""

    def test_the_response_is_returned_unchanged(self) -> None:
        sentinel = object()
        assert PrincipalMiddleware(lambda request: sentinel)(object()) is sentinel


class _Request:
    def __init__(self, request_id: str = "") -> None:
        self.META = {"HTTP_X_REQUEST_ID": request_id} if request_id else {}


class _Response(dict):
    pass


class TestRequestCorrelation:
    def test_a_view_sees_the_request_id_and_the_caller_gets_it_back(self) -> None:
        seen: dict[str, str] = {}

        def view(request):
            seen["id"] = request_id_var.get()
            seen["on_request"] = request.request_id
            return _Response()

        response = RequestContextMiddleware(view)(_Request("gateway-trace-1"))
        assert seen["id"] == "gateway-trace-1"
        assert seen["on_request"] == "gateway-trace-1"
        assert response["X-Request-Id"] == "gateway-trace-1"

    def test_a_missing_header_mints_a_request_id(self) -> None:
        def view(request):
            return _Response()

        response = RequestContextMiddleware(view)(_Request())
        assert response["X-Request-Id"]
        assert request_id_var.get() == ""

    def test_a_raised_view_does_not_leak_the_request_id(self) -> None:
        def exploding(request):
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            RequestContextMiddleware(exploding)(_Request("leaky"))
        assert request_id_var.get() == ""


class TestJsonFormatter:
    def test_a_line_carries_the_bound_actor_and_request(self) -> None:
        import json
        import logging

        request_id_var.set("req-1")
        actor_id_var.set("officer_221")
        actor_role_var.set(Role.WELFARE_OFFICER.value)
        record = logging.LogRecord(
            name="manobal",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="scored",
            args=(),
            exc_info=None,
        )
        payload = json.loads(JsonFormatter().format(record))
        assert payload["request_id"] == "req-1"
        assert payload["actor_id"] == "officer_221"
        assert payload["actor_role"] == Role.WELFARE_OFFICER.value
        assert payload["message"] == "scored"
