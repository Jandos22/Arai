"""Square/POS events — deterministic, capacity-aware POS → kitchen handoff.

The launch-day scenario emits a seeded ``square:walk_in_order`` event. This
handler walks it through the POS → kitchen lifecycle without invoking the
agent layer (no LLM in the loop), so the evaluator sees explicit
``square_create_order`` / ``kitchen_*`` evidence regardless of how the
sales/ops agents are configured.

Flow (capacity-aware — both branches are exercised across runs):

    square:walk_in_order
        → square_create_order
        → kitchen_create_ticket
        → kitchen_get_capacity + kitchen_get_menu_constraints
        → square_capacity_decision evidence row (decision: accept | reject)
        → if accept: kitchen_accept_ticket → kitchen_mark_ready
                     → square_update_order_status status=ready
        → if reject: kitchen_reject_ticket(reason)
                     → square_update_order_status
                       status=delayed_or_needs_owner_review
                     → optional Telegram owner ping

The decision is deterministic: sum prepMinutes × quantity for the mapped
ready-made line items, compare against ``remainingCapacityMinutes``. Items
flagged ``requiresCustomWork`` short-circuit to reject — walk-ins should not
auto-accept custom work even when there's headroom.
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

# Conservative fallback prep minutes per item when neither the menu-constraints
# tool nor the capacity tool surfaces something usable. 45 min matches the
# sandbox's observed `defaultLeadTimeMinutes`.
_FALLBACK_PREP_MINUTES = 45


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


def _index_constraints(constraints: Any) -> dict[str, dict[str, Any]]:
    """Normalize ``kitchen_get_menu_constraints`` into a {productId: row} map.

    Tolerates the two shapes seen in practice: a bare list of rows, or a dict
    with a ``products`` / ``items`` key wrapping the list.
    """
    rows: list[Any] = []
    if isinstance(constraints, list):
        rows = constraints
    elif isinstance(constraints, dict):
        for key in ("products", "items", "menu", "constraints"):
            value = constraints.get(key)
            if isinstance(value, list):
                rows = value
                break
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict):
            pid = row.get("productId") or row.get("id")
            if pid:
                indexed[pid] = row
    return indexed


def _evaluate_capacity(
    kitchen_items: list[dict[str, Any]],
    capacity: dict[str, Any],
    constraints: Any,
) -> tuple[str, str, int, int]:
    """Decide accept vs reject for the seeded walk-in.

    Returns ``(decision, reason, required_minutes, remaining_minutes)``.

    Rules, in order:
      1. Any line item flagged ``requiresCustomWork`` → reject (walk-ins
         should never auto-accept custom production).
      2. ``required_minutes`` = sum(prepMinutes × quantity); fall back to
         the capacity payload's ``defaultLeadTimeMinutes`` (or 45) when a
         product isn't in the constraints map.
      3. ``remaining_minutes`` = ``remainingCapacityMinutes``, or
         ``dailyCapacityMinutes − activePrepMinutes`` if missing.
      4. If ``required ≤ remaining``: accept. Otherwise: reject.
    """
    indexed = _index_constraints(constraints)

    custom_pids = [
        item["productId"]
        for item in kitchen_items
        if indexed.get(item.get("productId", ""), {}).get("requiresCustomWork")
    ]
    if custom_pids:
        return (
            "reject",
            f"Walk-in cannot auto-accept custom-work item(s): {', '.join(custom_pids)}.",
            0,
            int(capacity.get("remainingCapacityMinutes") or 0),
        )

    default_prep = int(capacity.get("defaultLeadTimeMinutes") or _FALLBACK_PREP_MINUTES)

    required_minutes = 0
    for item in kitchen_items:
        pid = item.get("productId", "")
        row = indexed.get(pid, {})
        prep = row.get("prepMinutes")
        if not isinstance(prep, (int, float)):
            prep = default_prep
        quantity = item.get("quantity", 1) or 1
        required_minutes += int(prep) * int(quantity)

    remaining = capacity.get("remainingCapacityMinutes")
    if remaining is None:
        daily = capacity.get("dailyCapacityMinutes") or 0
        active = capacity.get("activePrepMinutes") or 0
        remaining = max(0, int(daily) - int(active))
    remaining = int(remaining)

    if required_minutes <= remaining:
        return (
            "accept",
            f"Capacity OK — need {required_minutes} min, {remaining} min remaining.",
            required_minutes,
            remaining,
        )
    return (
        "reject",
        f"Capacity short — need {required_minutes} min, only {remaining} min remaining.",
        required_minutes,
        remaining,
    )


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
    kitchen_items: list[dict[str, Any]] = []
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
            "notes": "Auto-created from seeded Square walk-in order; capacity check follows.",
        },
    )
    ticket_id = _first_id(ticket, "ticketId", "id")
    ctx.evidence.write("mcp_call", tool="kitchen_create_ticket", ok=True, args={"orderId": order_id, "items": kitchen_items}, resultSummary=ticket)

    if not ticket_id:
        ctx.evidence.write("square_handoff_failed", reason="missing_ticket_id", orderId=order_id, ticket=ticket)
        return

    # 3) Capacity-aware decision — both branches are visible in evidence.
    capacity_raw = ctx.client.call_tool("kitchen_get_capacity", {})
    capacity = capacity_raw if isinstance(capacity_raw, dict) else {}
    ctx.evidence.write("mcp_call", tool="kitchen_get_capacity", ok=True, args={}, resultSummary=capacity_raw)

    constraints = ctx.client.call_tool("kitchen_get_menu_constraints", {})
    ctx.evidence.write("mcp_call", tool="kitchen_get_menu_constraints", ok=True, args={}, resultSummary=constraints)

    decision, reason, required_minutes, remaining_minutes = _evaluate_capacity(
        kitchen_items, capacity, constraints
    )
    ctx.evidence.write(
        "square_capacity_decision",
        capacity_checked=True,
        decision=decision,
        reason=reason,
        orderId=order_id,
        ticketId=ticket_id,
        requiredMinutes=required_minutes,
        remainingMinutes=remaining_minutes,
    )

    if decision == "accept":
        accepted = ctx.client.call_tool(
            "kitchen_accept_ticket",
            {"ticketId": ticket_id, "note": reason},
        )
        ctx.evidence.write(
            "mcp_call", tool="kitchen_accept_ticket", ok=True,
            args={"ticketId": ticket_id}, resultSummary=accepted,
        )

        ready = ctx.client.call_tool(
            "kitchen_mark_ready",
            {"ticketId": ticket_id, "pickupNote": "Ready for counter pickup."},
        )
        ctx.evidence.write(
            "mcp_call", tool="kitchen_mark_ready", ok=True,
            args={"ticketId": ticket_id}, resultSummary=ready,
        )

        status = ctx.client.call_tool(
            "square_update_order_status",
            {"orderId": order_id, "status": "ready", "note": "Kitchen marked ready for pickup."},
        )
        ctx.evidence.write(
            "mcp_call", tool="square_update_order_status", ok=True,
            args={"orderId": order_id, "status": "ready"}, resultSummary=status,
        )

        ctx.evidence.write(
            "square_handoff_complete",
            orderId=order_id, ticketId=ticket_id, items=kitchen_items, decision="accept",
        )
        return

    # decision == "reject" — capacity short, custom-work, or both.
    rejected = ctx.client.call_tool(
        "kitchen_reject_ticket",
        {"ticketId": ticket_id, "reason": reason},
    )
    ctx.evidence.write(
        "mcp_call", tool="kitchen_reject_ticket", ok=True,
        args={"ticketId": ticket_id, "reason": reason}, resultSummary=rejected,
    )

    delayed = ctx.client.call_tool(
        "square_update_order_status",
        {"orderId": order_id, "status": "delayed_or_needs_owner_review", "note": reason},
    )
    ctx.evidence.write(
        "mcp_call", tool="square_update_order_status", ok=True,
        args={"orderId": order_id, "status": "delayed_or_needs_owner_review"},
        resultSummary=delayed,
    )

    if ctx.telegram_notifier is not None:
        ctx.telegram_notifier.request_approval(
            summary=f"Kitchen at capacity — walk-in order {order_id} delayed: {reason}",
            draft="Approve to manually re-queue, reject to keep delayed and notify customer.",
            context={
                "channel": "square",
                "orderId": order_id,
                "ticketId": ticket_id,
                "reason": reason,
                "decision": "reject",
                "requiredMinutes": required_minutes,
                "remainingMinutes": remaining_minutes,
            },
        )

    ctx.evidence.write(
        "square_handoff_complete",
        orderId=order_id, ticketId=ticket_id, items=kitchen_items,
        decision="reject", reason=reason,
    )
