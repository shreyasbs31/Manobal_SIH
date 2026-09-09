"""Tiny Zone 1 HTTP surface: sync forward and Tier-B inference.

The process holds no store and no identity credential. It validates a device
batch, posts it to Zone 2, and answers ``/v1/infer`` from the local stub.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from manobal_edge.gateway import CaptureForwarder, HttpCoreCaptures, SyncResult
from manobal_edge.inference import infer_turn


class EdgeHandler(BaseHTTPRequestHandler):
    server: EdgeServer

    def log_message(self, fmt: str, *args: object) -> None:
        del fmt, args

    def do_GET(self) -> None:
        if urlparse(self.path).path == "/healthz":
            self._json(200, {"status": "ok", "zone": 1})
            return
        self._json(404, {"code": "MB-4040", "detail": "not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        body = self._read_json()
        if path == "/v1/sync":
            self._sync(body)
            return
        if path == "/v1/infer":
            message = str(body.get("message") or "") if isinstance(body, dict) else ""
            self._json(200, infer_turn(message))
            return
        self._json(404, {"code": "MB-4040", "detail": "not found"})

    def _sync(self, body: object) -> None:
        if not isinstance(body, dict):
            self._json(422, {"code": "MB-4220", "detail": "expected an object"})
            return
        result: SyncResult = self.server.forwarder.forward(body)
        self._json(result.status_code, result.body)

    def _read_json(self) -> object:
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode())
        except json.JSONDecodeError:
            return {}

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class EdgeServer(ThreadingHTTPServer):
    def __init__(self, host: str, port: int, forwarder: CaptureForwarder) -> None:
        super().__init__((host, port), EdgeHandler)
        self.forwarder = forwarder


def serve(host: str, port: int, *, core_url: str, core_token: str) -> None:
    server = EdgeServer(
        host, port, CaptureForwarder(HttpCoreCaptures(core_url, token=core_token))
    )
    server.serve_forever()
