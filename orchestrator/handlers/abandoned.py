"""Abandoned-order scheduler tick.

Listens for ``schedule:abandoned_tick`` events emitted by the scenario
loop (or by an external cron). On each tick we:

1. Read ``square_recent_orders`` from the sandbox.
2. Filter to orders in ``pending_pickup`` state whose pickup window is
   ≤ ``ABANDON_LEAD_MINUTES`` from now (default 120) and not yet
   reminded.
3. For each, dispatch a synthetic ``whatsapp:follow_up_due`` event back
   into the dispatcher — re-using the existing follow-up handler that
   already knows how to draft the reminder + send via ``whatsapp_send``.

This keeps "abandoned-order detection" deterministic and inspectable
(every tick writes ``abandoned_scan`` evidence) while reusing the
already-shipped follow-up sender. No new MCP tools, no new templates.
"""
from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Any, Iterable

from ..dispatcher import HandlerContext

ABANDON_LEAD_MINUTES = 120
PENDING_STATES = {"pending_pickup", "pending", "ready", "ready_for_pickup", "scheduled"}


def handle(event: dict[str, Any], ctx: HandlerContext) -> None:
    """Process one ``schedule:abandoned_tick`` event."""
    payload = event.get("payload") or event
    now = _now_utc(payload.get("now"))
    lead_minutes = int(payload.get("leadMinutes") or ABANDON_LEAD_MINUTES)

    try:
        recent_orders = ctx.client.call_tool("square_recent_orders", {})
    except Exception as exc:  # noqa: BLE001
        ctx.evidence.mcp_call("square_recent_orders", args={}, ok=False, error=str(exc))
        ctx.evidence.write("abandoned_scan_failed", error=str(exc))
        return
    ctx.evidence.mcp_call("square_recent_orders", args={}, result_summary=recent_orders)

    candidates = list(_iter_pending_pickup(recent_orders, now, lead_minutes))
    ctx.evidence.write(
        "abandoned_scan",
        leadMinutes=lead_minutes,
        candidateCount=len(candidates),
        evidenceSources=["square_recent_orders"],
    )

    dispatcher = getattr(ctx, "_dispatcher", None)
    for candidate in candidates:
        synthetic = {
            "channel": "whatsapp",
            "type": "follow_up_due",
            "payload": {
                "to": candidate["phone"],
                "pickupAt": candidate["pickup_at"],
                "orderId": candidate["order_id"],
                "source": "abandoned_scheduler",
            },
        }
        ctx.evidence.write(
            "abandoned_follow_up_emitted",
            orderId=candidate["order_id"],
            pickupAt=candidate["pickup_at"],
            recipient=candidate["phone"],
            evidenceSources=["square_recent_orders"],
        )
        if callable(dispatcher):
            dispatcher(synthetic)


def _iter_pending_pickup(
    recent_orders: Any, now: datetime, lead_minutes: int
) -> Iterable[dict[str, Any]]:
    for order in _iter_orders(recent_orders):
        state = str(order.get("state") or order.get("status") or "").lower()
        if state and state not in PENDING_STATES:
            continue
        if order.get("reminderSentAt") or order.get("followUpSentAt"):
            continue
        pickup_raw = (
            order.get("pickupAt")
            or order.get("pickupTime")
            or order.get("pickup")
            or order.get("scheduledFor")
        )
        pickup_at = _parse_when(pickup_raw)
        if pickup_at is None:
            continue
        delta_min = (pickup_at - now).total_seconds() / 60.0
        if delta_min < 0 or delta_min > lead_minutes:
            continue
        phone = (
            order.get("phone")
            or order.get("customerPhone")
            or order.get("contact")
            or ""
        )
        if not phone:
            continue
        yield {
            "order_id": str(order.get("id") or order.get("orderId") or ""),
            "phone": str(phone),
            "pickup_at": str(pickup_raw),
            "delta_minutes": round(delta_min, 1),
        }


def _now_utc(override: Any) -> datetime:
    if isinstance(override, str):
        parsed = _parse_when(override)
        if parsed:
            return parsed
    return datetime.now(timezone.utc)


def _parse_when(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    cleaned = value.strip()
    # Normalize trailing Z to +00:00 for fromisoformat
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(cleaned)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _iter_orders(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                yield item
        return
    if isinstance(value, dict):
        for key in ("orders", "recentOrders", "items", "data"):
            nested = value.get(key)
            if isinstance(nested, list):
                for item in nested:
                    if isinstance(item, dict):
                        yield item
                return
        yield value
