"""Telegram owner UI — lightweight notifier for the orchestrator.

We deliberately keep this **simple and synchronous**: send a message,
optionally with an inline approve/reject keyboard, and store pending
approvals in memory keyed by callback_data. A separate long-poll
(``poll_callbacks``) drains updates once per scenario tick.

For richer interactions (e.g. /marketing slash command), the user can run
the standalone ``bots/`` wrappers — see ``docs/ARCHITECTURE.md``.

If ``TELEGRAM_BOT_TOKEN_OWNER`` and ``TELEGRAM_OWNER_CHAT_ID`` aren't set,
the notifier silently no-ops and writes evidence rows so the eval still
sees what *would* have been sent.
"""
from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

import httpx

from .evidence import EvidenceLogger

log = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


@dataclass
class PendingApproval:
    approval_id: str
    summary: str
    draft: str
    context: dict[str, Any]
    on_decision: Callable[[bool], None] | None = None
    decided: bool | None = None


@dataclass
class TelegramNotifier:
    token: str | None
    chat_id: str | None
    evidence: EvidenceLogger
    _client: httpx.Client = field(default_factory=lambda: httpx.Client(timeout=15.0), repr=False)
    _pending: dict[str, PendingApproval] = field(default_factory=dict)
    _last_update_id: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @classmethod
    def from_env(cls, evidence: EvidenceLogger) -> "TelegramNotifier":
        token = os.environ.get("TELEGRAM_BOT_TOKEN_OWNER") or os.environ.get(
            "TELEGRAM_BOT_TOKEN_OPS"
        )
        chat_id = os.environ.get("TELEGRAM_OWNER_CHAT_ID")
        if not token or not chat_id:
            log.warning(
                "Telegram not configured (TELEGRAM_BOT_TOKEN_OWNER + TELEGRAM_OWNER_CHAT_ID). "
                "Approvals will be auto-approved in dev; evidence still logged."
            )
        return cls(token=token, chat_id=chat_id, evidence=evidence)

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.chat_id)

    # ------------------------------------------------------------------ send

    def notify(self, text: str, **extra_evidence: Any) -> None:
        self.evidence.owner_msg("notify", summary=text[:200], **extra_evidence)
        if not self.enabled:
            return
        self._call("sendMessage", {"chat_id": self.chat_id, "text": text})

    def request_approval(
        self,
        summary: str,
        draft: str,
        context: dict[str, Any] | None = None,
        on_decision: Callable[[bool], None] | None = None,
    ) -> str:
        approval_id = uuid.uuid4().hex[:8]
        pending = PendingApproval(
            approval_id=approval_id,
            summary=summary,
            draft=draft,
            context=context or {},
            on_decision=on_decision,
        )
        with self._lock:
            self._pending[approval_id] = pending
        self.evidence.owner_msg(
            "approval_request",
            summary=summary,
            approvalId=approval_id,
            context=context or {},
        )
        if self.enabled:
            text = f"⚠️ *Approval needed*\n\n{summary}\n\n_Draft reply:_\n{draft}"
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "✅ Approve", "callback_data": f"approve:{approval_id}"},
                        {"text": "❌ Reject", "callback_data": f"reject:{approval_id}"},
                    ]
                ]
            }
            self._call(
                "sendMessage",
                {
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                    "reply_markup": keyboard,
                },
            )
        else:
            # Dev fallback: auto-approve so the loop keeps moving.
            self._resolve(approval_id, True, auto=True)
        return approval_id

    # ------------------------------------------------------------------ poll

    def poll_callbacks(self, max_wait_s: float = 0.5) -> int:
        """Drain pending callback queries. Returns number resolved."""
        if not self.enabled:
            return 0
        result = self._call(
            "getUpdates",
            {
                "offset": self._last_update_id + 1,
                "timeout": int(max_wait_s),
                "allowed_updates": ["callback_query"],
            },
        )
        if not result or "result" not in result:
            return 0
        resolved = 0
        for upd in result["result"]:
            self._last_update_id = max(self._last_update_id, upd["update_id"])
            cq = upd.get("callback_query")
            if not cq:
                continue
            data = cq.get("data", "")
            if ":" not in data:
                continue
            verdict, approval_id = data.split(":", 1)
            ok = verdict == "approve"
            self._resolve(approval_id, ok, auto=False)
            self._call("answerCallbackQuery", {"callback_query_id": cq["id"]})
            resolved += 1
        return resolved

    def wait_for_approval(self, approval_id: str, timeout_s: float = 60.0) -> bool:
        """Block (with polling) until approval_id is decided or timeout. Returns
        the verdict; on timeout, treats it as rejected."""
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            with self._lock:
                pending = self._pending.get(approval_id)
                if pending and pending.decided is not None:
                    return pending.decided
            self.poll_callbacks()
            time.sleep(0.5)
        # Timeout → reject
        self._resolve(approval_id, False, auto=False, reason="timeout")
        return False

    # ------------------------------------------------------------------ internals

    def _resolve(self, approval_id: str, verdict: bool, *, auto: bool, reason: str = "") -> None:
        with self._lock:
            pending = self._pending.get(approval_id)
            if pending is None or pending.decided is not None:
                return
            pending.decided = verdict
        self.evidence.owner_msg(
            "approval_resolution",
            f"{'approved' if verdict else 'rejected'} approval {approval_id}",
            approvalId=approval_id,
            verdict="approve" if verdict else "reject",
            auto=auto,
            reason=reason,
        )
        if pending.on_decision is not None:
            try:
                pending.on_decision(verdict)
            except Exception as exc:  # noqa: BLE001
                log.exception("on_decision callback failed: %s", exc)

    def _call(self, method: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        if not self.token:
            return None
        url = f"{TELEGRAM_API}/bot{self.token}/{method}"
        try:
            resp = self._client.post(url, json=payload)
        except httpx.HTTPError as exc:
            log.warning("telegram %s failed: %s", method, exc)
            return None
        try:
            return resp.json()
        except ValueError:
            log.warning("telegram %s non-JSON response", method)
            return None
