"""Kitchen events — capacity changes, ticket state transitions.

Most kitchen logic happens *after* a sales-agent ticket creation. This handler
is for cases where the world scenario surfaces a kitchen-side event we should
react to (new ticket auto-queued, capacity warning, etc.).
"""
from __future__ import annotations

from typing import Any

from ..dispatcher import HandlerContext


def handle(event: dict[str, Any], ctx: HandlerContext) -> None:
    payload = event.get("payload") or event
    etype = event.get("type", "kitchen_event")

    ctx.evidence.write("channel_inbound", channel="kitchen", subtype=etype, payload=payload)

    if etype == "ticket_pending_owner_approval" and ctx.telegram_notifier is not None:
        ticket = payload.get("ticket") or payload
        ctx.telegram_notifier.request_approval(
            summary=f"Kitchen ticket needs your approval: {ticket.get('customerName', '?')} "
            f"— {ticket.get('items', '?')}",
            draft="Approve to start prep, reject if we can't promise this.",
            context={"channel": "kitchen", "ticketId": ticket.get("ticketId")},
        )
        return

    if ctx.ops_runner is not None:
        prompt = (
            f"Kitchen event for HappyCake US: {etype}\n\n"
            f"Payload: {payload}\n\n"
            "Decide whether to call kitchen_accept_ticket / kitchen_reject_ticket / "
            "kitchen_mark_ready, or escalate to owner via Telegram. Use "
            "kitchen_get_capacity and kitchen_get_menu_constraints to validate "
            "any promise."
        )
        ctx.ops_runner.run(prompt, label=f"kitchen_{etype}")
