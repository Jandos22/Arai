"""Event-type → handler routing.

We keep this dumb on purpose: a single function decides which handler runs.
Handlers themselves stay pure-ish (just functions over `(event, ctx)`),
so unit tests are mechanical.
"""
from __future__ import annotations

import logging
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
        handler(event, ctx)

    return dispatch


def _key_for(event: dict[str, Any]) -> str:
    channel = event.get("channel", "world")
    etype = event.get("type", "unknown")
    return f"{channel}:{etype}"


def _fallback_key(event: dict[str, Any]) -> str:
    return event.get("channel", "world") + ":*"
