"""Local webhook adapter for Cloudflare/ngrok tunnel ingress.

This keeps the hackathon "webhooks tunnel home" runtime shape while routing
all events into the same dispatcher used by the sandbox world loop.
"""
from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable

from .evidence import EvidenceLogger

log = logging.getLogger(__name__)

Dispatch = Callable[[dict[str, Any]], None]

MAX_BODY_BYTES = 1_000_000


def normalize_whatsapp_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the dispatcher event shape for a WhatsApp webhook payload."""
    return {
        "channel": "whatsapp",
        "type": "inbound_message",
        "payload": payload,
    }


def normalize_instagram_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the dispatcher event shape for an Instagram webhook payload."""
    explicit_type = payload.get("type")
    if explicit_type in {"dm", "comment"}:
        etype = explicit_type
    elif payload.get("comment") or payload.get("commentId") or payload.get("comment_id"):
        etype = "comment"
    else:
        etype = "dm"
    return {
        "channel": "instagram",
        "type": etype,
        "payload": payload,
    }


def make_webhook_server(
    host: str,
    port: int,
    dispatch: Dispatch,
    evidence: EvidenceLogger,
) -> ThreadingHTTPServer:
    """Create a stdlib HTTP server bound to ``host:port``."""

    class WebhookHandler(BaseHTTPRequestHandler):
        server_version = "AraiWebhook/0.1"

        def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
            if self.path != "/healthz":
                self._send_json(404, {"ok": False, "error": "not_found"})
                return
            self._send_json(200, {"ok": True, "runId": evidence.run_id})

        def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
            if self.path not in {"/webhooks/whatsapp", "/webhooks/instagram"}:
                self._send_json(404, {"ok": False, "error": "not_found"})
                return

            try:
                payload = self._read_json_body()
            except ValueError as exc:
                evidence.write(
                    "webhook_rejected",
                    path=self.path,
                    reason=str(exc),
                )
                self._send_json(400, {"ok": False, "error": str(exc)})
                return

            event = (
                normalize_whatsapp_payload(payload)
                if self.path == "/webhooks/whatsapp"
                else normalize_instagram_payload(payload)
            )
            evidence.write(
                "webhook_inbound",
                path=self.path,
                channel=event["channel"],
                type=event["type"],
                payload=payload,
            )

            try:
                dispatch(event)
            except Exception as exc:  # pragma: no cover - defensive boundary
                log.exception("webhook dispatch failed")
                evidence.write(
                    "webhook_error",
                    path=self.path,
                    channel=event["channel"],
                    type=event["type"],
                    error=str(exc),
                )
                self._send_json(500, {"ok": False, "error": "dispatch_failed"})
                return

            self._send_json(200, {"ok": True, "event": {"channel": event["channel"], "type": event["type"]}})

        def log_message(self, fmt: str, *args: Any) -> None:
            log.info("webhook %s - %s", self.address_string(), fmt % args)

        def _read_json_body(self) -> dict[str, Any]:
            length_header = self.headers.get("Content-Length")
            if not length_header:
                raise ValueError("missing_body")
            try:
                length = int(length_header)
            except ValueError as exc:
                raise ValueError("bad_content_length") from exc
            if length > MAX_BODY_BYTES:
                raise ValueError("body_too_large")

            raw = self.rfile.read(length)
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("invalid_json") from exc
            if not isinstance(payload, dict):
                raise ValueError("json_body_must_be_object")
            return payload

        def _send_json(self, status: int, body: dict[str, Any]) -> None:
            encoded = json.dumps(body, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return ThreadingHTTPServer((host, port), WebhookHandler)


def serve_webhooks(host: str, port: int, dispatch: Dispatch, evidence: EvidenceLogger) -> None:
    """Serve webhook requests until interrupted."""
    server = make_webhook_server(host, port, dispatch, evidence)
    log.info("webhook server listening on http://%s:%s", host, port)
    try:
        server.serve_forever()
    finally:
        server.server_close()
