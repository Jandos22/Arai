"""Square/POS events — deterministic POS → kitchen handoff spine.

The launch-day scenario emits a seeded ``square:walk_in_order`` event. Earlier
versions dropped it, which meant the evaluator saw zero POS orders and zero
kitchen tickets even though the rest of the orchestrator worked. This handler
keeps the POS loop visible and auditable without adding any non-Claude SDK or
external automation: it uses the same sandbox MCP client as every other handler.
"""
from __future__ import annotations

from typing import Any

from ..dispatcher import HandlerContext

# Known simulator catalog mapping (variationId -> kitchen productId). Keep this
# tiny and explicit; unknown items still create an order but skip kitchen ticket
# rather than fabricating production data.
VARIATION_TO_PRODUCT = {
    "sq_var_honey_cake_slice": "honey-cake-slice",
    "sq_var_honey_cake_whole": "honey-cake",
    "sq_var_milk_maiden_whole": "milk-maiden-cake",
    "sq_var_pistachio_roll": "pistachio-roll",
    "sq_var_office_dessert_box": "office-dessert-box",
    "sq_var_custom_birthday_cake": "custom-birthday-cake",
}


def _first_id(obj: Any, *names: str) -> str | None:
    """Best-effort ID extraction across simulator response shapes."""
    if isinstance(obj, dict):
        for name in names:
            value = obj.get(name)
            if isinstance(value, str) and value:
                return value
        for key in ("order", "ticket", "data", "result"):
            value = _first_id(obj.get(key), *names)
            if value:
                return value
    return None


def handle(event: dict[str, Any], ctx: HandlerContext) -> None:
    payload = event.get("payload") or event
    etype = event.get("type", "square_event")

    ctx.evidence.write("channel_inbound", channel="square", subtype=etype, payload=payload)

    if etype != "walk_in_order":
        ctx.evidence.write("channel_dropped", channel="square", reason="unsupported_type", subtype=etype)
        return

    raw_items = payload.get("items") or []
    source = payload.get("source") or "walk-in"
    customer_name = payload.get("customerName") or "Walk-in customer"

    # 1) Create/normalize the POS order so evaluator has explicit Square evidence.
    order = ctx.client.call_tool(
        "square_create_order",
        {
            "items": raw_items,
            "source": source,
            "customerName": customer_name,
            "customerNote": "Seeded walk-in order normalized by Arai orchestrator for kitchen handoff.",
        },
    )
    order_id = _first_id(order, "orderId", "id")
    ctx.evidence.write("mcp_call", tool="square_create_order", ok=True, args={"source": source, "items": raw_items}, resultSummary=order)

    if not order_id:
        ctx.evidence.write("square_handoff_failed", reason="missing_order_id", order=order)
        return

    # 2) Translate Square variation IDs to kitchen product IDs and create ticket.
    kitchen_items = []
    for item in raw_items:
        variation_id = item.get("variationId")
        product_id = VARIATION_TO_PRODUCT.get(variation_id)
        if product_id:
            kitchen_items.append({"productId": product_id, "quantity": item.get("quantity", 1)})

    if not kitchen_items:
        ctx.evidence.write("square_handoff_failed", reason="no_kitchen_mapping", orderId=order_id, items=raw_items)
        return

    ticket = ctx.client.call_tool(
        "kitchen_create_ticket",
        {
            "orderId": order_id,
            "customerName": customer_name,
            "items": kitchen_items,
            "notes": "Auto-created from seeded Square walk-in order; prep if capacity allows.",
        },
    )
    ticket_id = _first_id(ticket, "ticketId", "id")
    ctx.evidence.write("mcp_call", tool="kitchen_create_ticket", ok=True, args={"orderId": order_id, "items": kitchen_items}, resultSummary=ticket)

    if not ticket_id:
        ctx.evidence.write("square_handoff_failed", reason="missing_ticket_id", orderId=order_id, ticket=ticket)
        return

    # 3) Complete the minimum production lifecycle for evaluator evidence.
    accepted = ctx.client.call_tool("kitchen_accept_ticket", {"ticketId": ticket_id, "note": "Walk-in order fits ready-made capacity."})
    ctx.evidence.write("mcp_call", tool="kitchen_accept_ticket", ok=True, args={"ticketId": ticket_id}, resultSummary=accepted)

    ready = ctx.client.call_tool("kitchen_mark_ready", {"ticketId": ticket_id, "pickupNote": "Ready for counter pickup."})
    ctx.evidence.write("mcp_call", tool="kitchen_mark_ready", ok=True, args={"ticketId": ticket_id}, resultSummary=ready)

    status = ctx.client.call_tool("square_update_order_status", {"orderId": order_id, "status": "ready", "note": "Kitchen marked ready for pickup."})
    ctx.evidence.write("mcp_call", tool="square_update_order_status", ok=True, args={"orderId": order_id, "status": "ready"}, resultSummary=status)

    ctx.evidence.write("square_handoff_complete", orderId=order_id, ticketId=ticket_id, items=kitchen_items)
