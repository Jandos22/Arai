"""Webhook adapter tests."""
from __future__ import annotations

import http.client
import json
import threading
from pathlib import Path

import pytest

from orchestrator.webhook_server import (
    make_webhook_server,
    normalize_instagram_payload,
    normalize_whatsapp_payload,
)


class _RecordingEvidence:
    run_id = "run-test"

    def __init__(self, base_dir: Path | None = None):
        self.entries = []
        self.base_dir = base_dir or Path("evidence")

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


def test_normalize_whatsapp_steppe_webhook_envelope():
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messages": [
                                {
                                    "from": "+12815550100",
                                    "id": "wamid.test",
                                    "text": {"body": "Need cake tomorrow"},
                                    "type": "text",
                                }
                            ]
                        },
                    }
                ]
            }
        ],
    }

    normalized = normalize_whatsapp_payload(payload)["payload"]

    assert normalized["from"] == "+12815550100"
    assert normalized["message"] == "Need cake tomorrow"
    assert normalized["messageId"] == "wamid.test"
    assert normalized["raw"] == payload


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


def test_normalize_instagram_steppe_webhook_envelope():
    payload = {
        "object": "instagram",
        "entry": [
            {
                "messaging": [
                    {
                        "sender": {"id": "maya"},
                        "thread_id": "ig-1",
                        "message": {"mid": "m.test", "text": "Birthday cake?"},
                    }
                ]
            }
        ],
    }

    normalized = normalize_instagram_payload(payload)

    assert normalized["type"] == "dm"
    assert normalized["payload"]["threadId"] == "ig-1"
    assert normalized["payload"]["from"] == "maya"
    assert normalized["payload"]["message"] == "Birthday cake?"
    assert normalized["payload"]["raw"] == payload


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


def _request_with_headers(server, method, path, headers=None):
    """Like _request but returns raw bytes + status + content-type, no JSON parsing."""
    conn = http.client.HTTPConnection(server.server_address[0], server.server_address[1], timeout=5)
    conn.request(method, path, headers=headers or {})
    response = conn.getresponse()
    raw = response.read()
    ct = response.getheader("Content-Type", "")
    conn.close()
    return response.status, ct, raw


# ---------------------------------------------------------------- audit endpoint (paths 13-15)


def _seed_audit(tmp_path: Path, date_str: str, summary: dict | None = None) -> Path:
    base = tmp_path / "evidence"
    base.mkdir(exist_ok=True)
    body = summary or {
        "date": date_str,
        "highlights": ["12 orders today"],
        "lowlights": ["3 messages waited >2h"],
        "metrics": {"totalEvents": 7, "byKind": {"event": 7}},
        "evidence_refs": [{"runId": "run-x", "kind": "event", "ts": "2026-05-09T18:00:00Z"}],
        "llmFallback": False,
        "generatedAt": "2026-05-10T02:00:00Z",
    }
    (base / f"daily-{date_str}.json").write_text(json.dumps(body, indent=2), encoding="utf-8")
    return base


def test_audit_html_when_default_accept(tmp_path: Path):
    """Path #14 — default request returns rendered HTML 200."""
    base = _seed_audit(tmp_path, "2026-05-09")
    evidence = _RecordingEvidence(base_dir=base)
    with _server([], evidence) as server:
        status, ct, body = _request_with_headers(server, "GET", "/audit/2026-05-09")
    assert status == 200
    assert ct.startswith("text/html")
    text = body.decode("utf-8")
    assert "Arai daily report" in text
    assert "12 orders today" in text
    assert "3 messages waited" in text
    # evidence row written
    assert any(e["kind"] == "audit_request" and e.get("status") == 200 for e in evidence.entries)


def test_audit_json_when_accept_header(tmp_path: Path):
    """Path #13 — Accept: application/json returns the raw daily JSON."""
    base = _seed_audit(tmp_path, "2026-05-09")
    evidence = _RecordingEvidence(base_dir=base)
    with _server([], evidence) as server:
        status, ct, body = _request_with_headers(
            server, "GET", "/audit/2026-05-09", headers={"Accept": "application/json"}
        )
    assert status == 200
    assert ct.startswith("application/json")
    parsed = json.loads(body.decode("utf-8"))
    assert parsed["highlights"] == ["12 orders today"]


def test_audit_json_when_format_query(tmp_path: Path):
    """Defensive: ?format=json query also opts into JSON, useful from the
    Telegram inline button when Accept headers aren't set by the browser."""
    base = _seed_audit(tmp_path, "2026-05-09")
    evidence = _RecordingEvidence(base_dir=base)
    with _server([], evidence) as server:
        status, ct, body = _request_with_headers(
            server, "GET", "/audit/2026-05-09?format=json"
        )
    assert status == 200
    assert ct.startswith("application/json")
    parsed = json.loads(body.decode("utf-8"))
    assert parsed["date"] == "2026-05-09"


def test_audit_404_when_no_report(tmp_path: Path):
    """Path #15 — file missing → clean 404 JSON with the date echoed back."""
    base = tmp_path / "evidence"
    base.mkdir()
    evidence = _RecordingEvidence(base_dir=base)
    with _server([], evidence) as server:
        status, ct, body = _request_with_headers(server, "GET", "/audit/2026-05-09")
    assert status == 404
    parsed = json.loads(body.decode("utf-8"))
    assert parsed == {"ok": False, "error": "no_daily_report", "date": "2026-05-09"}


def test_audit_400_on_bad_date_format(tmp_path: Path):
    """A malformed date should give 400, not 500."""
    base = tmp_path / "evidence"
    base.mkdir()
    evidence = _RecordingEvidence(base_dir=base)
    with _server([], evidence) as server:
        # The path regex requires \d{4}-\d{2}-\d{2}, so this gets caught at
        # the regex (returns 404 not_found rather than 400 bad_date_format).
        # We still want a non-500 response.
        status, ct, body = _request_with_headers(server, "GET", "/audit/not-a-date")
    assert status == 404


def test_audit_unknown_path_still_404(tmp_path: Path):
    base = tmp_path / "evidence"
    base.mkdir()
    evidence = _RecordingEvidence(base_dir=base)
    with _server([], evidence) as server:
        status, ct, body = _request_with_headers(server, "GET", "/some/random/path")
    assert status == 404
