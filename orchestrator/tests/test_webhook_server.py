"""Webhook adapter tests."""
from __future__ import annotations

import http.client
import json
import threading

from orchestrator.webhook_server import (
    make_webhook_server,
    normalize_instagram_payload,
    normalize_whatsapp_payload,
)


class _RecordingEvidence:
    run_id = "run-test"

    def __init__(self):
        self.entries = []

    def write(self, kind, **fields):
        self.entries.append({"kind": kind, **fields})


def test_normalize_whatsapp_from_message():
    payload = {"from": "+12815550100", "message": "Do you have honey cake?"}

    assert normalize_whatsapp_payload(payload) == {
        "channel": "whatsapp",
        "type": "inbound_message",
        "payload": payload,
    }


def test_normalize_whatsapp_phone_text():
    payload = {"phone": "+12815550100", "text": "Need cake tomorrow"}

    assert normalize_whatsapp_payload(payload)["payload"] == payload


def test_normalize_instagram_dm():
    payload = {"threadId": "ig-1", "from": "maya", "message": "Birthday cake?"}

    assert normalize_instagram_payload(payload) == {
        "channel": "instagram",
        "type": "dm",
        "payload": payload,
    }


def test_normalize_instagram_comment():
    payload = {"commentId": "c-1", "username": "maya", "comment": "Looks good"}

    assert normalize_instagram_payload(payload)["type"] == "comment"


def test_healthz_returns_ok():
    evidence = _RecordingEvidence()
    with _server([], evidence) as server:
        status, body = _request(server, "GET", "/healthz")

    assert status == 200
    assert body == {"ok": True, "runId": "run-test"}


def test_whatsapp_post_dispatches_normalized_event():
    calls = []
    evidence = _RecordingEvidence()
    with _server(calls, evidence) as server:
        status, body = _request(
            server,
            "POST",
            "/webhooks/whatsapp",
            {"from": "+12815550100", "message": "Honey cake?"},
        )

    assert status == 200
    assert body["event"] == {"channel": "whatsapp", "type": "inbound_message"}
    assert calls == [
        {
            "channel": "whatsapp",
            "type": "inbound_message",
            "payload": {"from": "+12815550100", "message": "Honey cake?"},
        }
    ]
    assert any(e["kind"] == "webhook_inbound" for e in evidence.entries)


def test_instagram_post_dispatches_normalized_event():
    calls = []
    evidence = _RecordingEvidence()
    with _server(calls, evidence) as server:
        status, body = _request(
            server,
            "POST",
            "/webhooks/instagram",
            {"threadId": "ig-1", "from": "maya", "message": "Cake?"},
        )

    assert status == 200
    assert body["event"] == {"channel": "instagram", "type": "dm"}
    assert calls[0]["channel"] == "instagram"
    assert calls[0]["type"] == "dm"


def test_malformed_json_returns_400():
    calls = []
    evidence = _RecordingEvidence()
    with _server(calls, evidence) as server:
        status, body = _raw_request(server, "POST", "/webhooks/whatsapp", b"{")

    assert status == 400
    assert body == {"error": "invalid_json", "ok": False}
    assert calls == []


class _server:
    def __init__(self, calls, evidence):
        self.calls = calls
        self.evidence = evidence
        self.server = None
        self.thread = None

    def __enter__(self):
        def dispatch(event):
            self.calls.append(event)

        self.server = make_webhook_server("127.0.0.1", 0, dispatch, self.evidence)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self.server

    def __exit__(self, *_exc):
        assert self.server is not None
        self.server.shutdown()
        self.server.server_close()
        assert self.thread is not None
        self.thread.join(timeout=2)


def _request(server, method, path, payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    return _raw_request(server, method, path, body)


def _raw_request(server, method, path, body):
    conn = http.client.HTTPConnection(server.server_address[0], server.server_address[1], timeout=5)
    headers = {}
    if body is not None:
        headers["Content-Type"] = "application/json"
    conn.request(method, path, body=body, headers=headers)
    response = conn.getresponse()
    raw = response.read()
    conn.close()
    return response.status, json.loads(raw.decode("utf-8"))
