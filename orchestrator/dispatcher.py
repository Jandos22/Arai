"""Event-type → handler routing.

We keep this dumb on purpose: a single function decides which handler runs.
Handlers themselves stay pure-ish (just functions over `(event, ctx)`),
so unit tests are mechanical.
"""
from __future__ import annotations

import logging
import traceback
from dataclasses import dataclass
from typing import Any, Callable

from .claude_runner import ClaudeRunner
from .customers import CustomerStore
from .evidence import EvidenceLogger
from .mcp_client import MCPClient

log = logging.getLogger(__name__)


@dataclass
class HandlerContext:
    """Bag of dependencies handlers may need."""

    client: MCPClient
    evidence: EvidenceLogger
    sales_runner: ClaudeRunner | None = None
    ops_runner: ClaudeRunner | None = None
    marketing_runner: ClaudeRunner | None = None
    telegram_notifier: Any | None = None  # set by main.py if telegram is wired
    customers: CustomerStore | None = None


Handler = Callable[[dict[str, Any], HandlerContext], None]


def make_dispatcher(ctx: HandlerContext, table: dict[str, Handler]) -> Callable[[dict[str, Any]], None]:
    """Return a single-arg dispatch callable closing over ``ctx`` + ``table``."""

    def dispatch(event: dict[str, Any]) -> None:
        key = _key_for(event)
        handler = table.get(key) or table.get(_fallback_key(event)) or table.get("*")
        if handler is None:
            log.warning("No handler for %s — dropping", key)
            ctx.evidence.write("dispatch_drop", reason="no_handler", key=key, event=event)
            return
        log.info("dispatch %s -> %s", key, handler.__name__)
        try:
            handler(event, ctx)
        except Exception as exc:  # noqa: BLE001 — boundary: log + continue
            tb = traceback.format_exc(limit=8)
            log.exception("handler %s failed for %s", handler.__name__, key)
            ctx.evidence.write(
                "handler_error",
                key=key,
                handler=handler.__name__,
                error=f"{type(exc).__name__}: {exc}",
                traceback=tb,
                event=event,
            )
            notifier = getattr(ctx, "telegram_notifier", None)
            if notifier is not None:
                try:
                    notifier.notify(
                        f"⚠️ Handler error: {handler.__name__} on {key}\n"
                        f"{type(exc).__name__}: {exc}",
                        kind="handler_error",
                    )
                except Exception:  # noqa: BLE001 — never let notifier mask the original
                    log.exception("telegram notify failed while reporting handler_error")

    return dispatch


def _key_for(event: dict[str, Any]) -> str:
    channel = event.get("channel", "world")
    etype = event.get("type", "unknown")
    return f"{channel}:{etype}"


def _fallback_key(event: dict[str, Any]) -> str:
    return event.get("channel", "world") + ":*"
