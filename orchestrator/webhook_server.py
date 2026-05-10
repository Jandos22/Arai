"""Local webhook adapter for Cloudflare/ngrok tunnel ingress.

This keeps the hackathon "webhooks tunnel home" runtime shape while routing
all events into the same dispatcher used by the sandbox world loop.

Also serves the read-only daily-report audit endpoint. Judges visit
``GET /audit/<date>`` over the tunnel to verify the daily report system
runs without touching the owner's Telegram. The same surface returns JSON
when ``Accept: application/json`` is set so other agents can read it
programmatically.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date as date_cls
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from html import escape
from typing import Any, Callable

from .daily_report import daily_report_path
from .evidence import EvidenceLogger

log = logging.getLogger(__name__)

Dispatch = Callable[[dict[str, Any]], None]

MAX_BODY_BYTES = 1_000_000

_AUDIT_PATH_RE = re.compile(r"^/audit/(\d{4}-\d{2}-\d{2})/?$")


def _render_audit_html(d: date_cls, summary: dict[str, Any]) -> str:
    """Inline HTML view of one daily report. No deps, no CDN, no JS."""
    title = f"Arai daily report — {d.isoformat()}"
    rows: list[str] = []
    rows.append("<!doctype html>")
    rows.append('<html lang="en"><head><meta charset="utf-8">')
    rows.append(f"<title>{escape(title)}</title>")
    rows.append(
        "<style>body{font-family:system-ui,sans-serif;max-width:720px;"
        "margin:2rem auto;padding:0 1rem;color:#222;line-height:1.5}"
        "h1{font-size:1.4rem;margin-bottom:.2rem}"
        "h2{font-size:1.05rem;margin-top:1.6rem;border-bottom:1px solid #ddd;padding-bottom:.2rem}"
        ".muted{color:#666;font-size:.9rem}"
        "ul{padding-left:1.2rem}"
        "table{border-collapse:collapse;font-size:.9rem}"
        "th,td{padding:.2rem .8rem;border:1px solid #ddd;text-align:left}"
        ".fallback{background:#fff8d9;border:1px solid #d9c774;padding:.6rem .8rem;"
        "border-radius:6px;margin:1rem 0;color:#7a5b00}"
        "</style></head><body>"
    )
    rows.append(f"<h1>☀️ {escape(title)}</h1>")
    gen = summary.get("generatedAt")
    if gen:
        rows.append(f'<div class="muted">Generated at {escape(str(gen))} UTC</div>')

    if summary.get("llmFallback"):
        reason = escape(str(summary.get("fallbackReason") or "unknown"))
        rows.append(
            f'<div class="fallback">⚠️ LLM summary unavailable ({reason}). '
            f"Showing deterministic counts only.</div>"
        )

    highs = summary.get("highlights") or []
    if highs:
        rows.append("<h2>Highlights</h2><ul>")
        for h in highs:
            rows.append(f"<li>✅ {escape(str(h))}</li>")
        rows.append("</ul>")

    lows = summary.get("lowlights") or []
    if lows:
        rows.append("<h2>Lowlights</h2><ul>")
        for low in lows:
            rows.append(f"<li>⚠️ {escape(str(low))}</li>")
        rows.append("</ul>")

    metrics = summary.get("metrics") or {}
    if metrics:
        rows.append("<h2>Metrics</h2><table><tbody>")
        for k, v in metrics.items():
            rows.append(f"<tr><th>{escape(str(k))}</th><td>{escape(json.dumps(v))}</td></tr>")
        rows.append("</tbody></table>")

    refs = summary.get("evidence_refs") or []
    if refs:
        rows.append("<h2>Evidence refs</h2><ul>")
        for r in refs:
            rows.append(f"<li><code>{escape(json.dumps(r, sort_keys=True))}</code></li>")
        rows.append("</ul>")

    rows.append('<p class="muted"><a href="?format=json">Raw JSON</a></p>')
    rows.append("</body></html>")
    return "\n".join(rows)


def _wants_json(accept_header: str | None, query: str) -> bool:
    """Trivial content negotiation: explicit ``Accept: application/json`` or
    ``?format=json`` → JSON. Default → HTML."""
    if "format=json" in (query or ""):
        return True
    if not accept_header:
        return False
    accept = accept_header.lower()
    if "application/json" in accept and "text/html" not in accept:
        return True
    return False


def normalize_whatsapp_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the dispatcher event shape for a WhatsApp webhook payload."""
    normalized = payload
    entries = payload.get("entry")
    if isinstance(entries, list) and entries:
        changes = entries[0].get("changes") if isinstance(entries[0], dict) else None
        if isinstance(changes, list) and changes:
            value = changes[0].get("value") if isinstance(changes[0], dict) else None
            messages = value.get("messages") if isinstance(value, dict) else None
            if isinstance(messages, list) and messages:
                message = messages[0]
                if isinstance(message, dict):
                    normalized = {
                        "from": message.get("from"),
                        "message": ((message.get("text") or {}).get("body") if isinstance(message.get("text"), dict) else None)
                        or message.get("body")
                        or message.get("message")
                        or "",
                        "messageId": message.get("id"),
                        "raw": payload,
                    }
    return {
        "channel": "whatsapp",
        "type": "inbound_message",
        "payload": normalized,
    }


def normalize_instagram_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the dispatcher event shape for an Instagram webhook payload."""
    normalized = payload
    entries = payload.get("entry")
    if isinstance(entries, list) and entries:
        messaging = entries[0].get("messaging") if isinstance(entries[0], dict) else None
        if isinstance(messaging, list) and messaging:
            event = messaging[0]
            if isinstance(event, dict):
                message = event.get("message") if isinstance(event.get("message"), dict) else {}
                sender = event.get("sender") if isinstance(event.get("sender"), dict) else {}
                normalized = {
                    "threadId": event.get("thread_id") or event.get("threadId"),
                    "from": sender.get("id") or event.get("from"),
                    "message": message.get("text") or event.get("text") or "",
                    "messageId": message.get("mid"),
                    "raw": payload,
                }

    explicit_type = normalized.get("type")
    if explicit_type in {"dm", "comment"}:
        etype = explicit_type
    elif normalized.get("comment") or normalized.get("commentId") or normalized.get("comment_id"):
        etype = "comment"
    else:
        etype = "dm"
    return {
        "channel": "instagram",
        "type": etype,
        "payload": normalized,
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
            # Strip query string for path matching, keep it for content-negotiation.
            raw_path, _, query = self.path.partition("?")

            if raw_path == "/healthz":
                self._send_json(200, {"ok": True, "runId": evidence.run_id})
                return

            audit_match = _AUDIT_PATH_RE.match(raw_path)
            if audit_match:
                self._serve_audit(audit_match.group(1), query)
                return

            self._send_json(404, {"ok": False, "error": "not_found"})

        def _serve_audit(self, date_str: str, query: str) -> None:
            try:
                d = date_cls.fromisoformat(date_str)
            except ValueError:
                self._send_json(400, {"ok": False, "error": "bad_date_format"})
                return

            path = daily_report_path(d, base_dir=evidence.base_dir)
            if not path.exists():
                evidence.write("audit_request", date=date_str, status=404)
                self._send_json(
                    404, {"ok": False, "error": "no_daily_report", "date": date_str}
                )
                return

            try:
                summary = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                log.warning("audit page failed to read %s: %s", path, exc)
                evidence.write(
                    "audit_request", date=date_str, status=500, error=str(exc)
                )
                self._send_json(500, {"ok": False, "error": "report_unreadable"})
                return

            evidence.write("audit_request", date=date_str, status=200)

            if _wants_json(self.headers.get("Accept"), query):
                self._send_json(200, summary)
                return

            html = _render_audit_html(d, summary).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(html)

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
