"""The edge rejects identifiers and oversized batches before they reach Zone 2."""

from __future__ import annotations

from manobal_edge.gateway import CaptureForwarder, SyncResult, validate_batch
from manobal_edge.inference import infer_turn


class FakeCore:
    def __init__(self) -> None:
        self.payloads: list[dict] = []

    def post_captures(self, payload: dict) -> SyncResult:
        self.payloads.append(payload)
        return SyncResult(accepted=True, status_code=202, body={"accepted": 1})


def test_a_clean_batch_is_forwarded() -> None:
    core = FakeCore()
    result = CaptureForwarder(core).forward(
        {
            "subject_token": "st_000001",
            "client_batch_id": "dev-1",
            "items": [{"kind": "bio", "metric_code": "resting_hr_nightly", "value": 70}],
        }
    )
    assert result.accepted is True
    assert core.payloads


def test_identifiers_are_refused() -> None:
    assert validate_batch(
        {
            "subject_token": "st_000001",
            "client_batch_id": "dev-2",
            "items": [{"kind": "bio", "service_no": "CRPF-1", "value": 1}],
        }
    )


def test_crisis_language_is_flagged_without_a_diagnosis() -> None:
    result = infer_turn("I want to die")
    assert result["crisis"] is True
    assert "diagnos" not in str(result["reply"]).lower()


def test_the_edge_http_surface_forwards_a_clean_batch() -> None:
    from http.client import HTTPConnection
    from threading import Thread

    from manobal_edge.server import EdgeServer

    core = FakeCore()
    server = EdgeServer("127.0.0.1", 0, CaptureForwarder(core))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        conn = HTTPConnection(str(host), int(port), timeout=2)
        try:
            conn.request(
                "POST",
                "/v1/sync",
                body='{"subject_token":"st_1","client_batch_id":"b","items":[{"kind":"bio","value":1,"metric_code":"hr"}]}',
                headers={"Content-Type": "application/json"},
            )
            response = conn.getresponse()
            response.read()
            assert response.status == 202
            assert core.payloads
        finally:
            conn.close()
    finally:
        server.shutdown()
        server.server_close()
