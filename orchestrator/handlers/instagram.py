"""Instagram DM/comment handler.

Same shape as WhatsApp: build prompt, delegate to sales agent. IG-specific:
post-publishing flow is owner-gated (schedule → owner approval via Telegram
→ ``instagram_publish_post``). Inbound handling here is just DM + comment.
"""
from __future__ import annotations

import json
from typing import Any

from ..customers import is_greeting, propose_reorder
from ..dispatcher import HandlerContext
from .whatsapp import _maybe_upsert_profile, _safe_recent_orders, _send_proposed_reorder


def handle(event: dict[str, Any], ctx: HandlerContext) -> None:
    payload = event.get("payload") or event
    # IG events arrive in several shapes depending on whether they were
    # injected via instagram_inject_dm (DM), instagram_inject_comment, or
    # surfaced organically by the scenario. Try every key the launch-kit
    # tools document.
    thread = (
        payload.get("threadId")
        or payload.get("thread")
        or payload.get("conversationId")
        or payload.get("threadID")
        or event.get("threadId")
    )
    sender = (
        payload.get("from")
        or payload.get("user")
        or payload.get("username")
        or payload.get("igHandle")
        or "unknown"
    )
    body = (
        payload.get("message")
        or payload.get("text")
        or payload.get("comment")
        or payload.get("body")
        or ""
    )
    comment_id = payload.get("commentId") or payload.get("comment_id")
    etype = event.get("type", "dm")

    ctx.evidence.write(
        "channel_inbound",
        channel="instagram",
        subtype=etype,
        threadId=thread,
        commentId=comment_id,
        sender=sender,
        bodyPreview=body[:200],
    )

    if not body and not thread and not comment_id:
        ctx.evidence.write(
            "channel_dropped",
            channel="instagram",
            reason="empty_payload",
            event_keys=sorted(payload.keys()) if isinstance(payload, dict) else [],
        )
        return

    # IG identity: prefer the @handle for profile keys (it's stable across
    # threads), fall back to the threadId so we still get a profile row.
    identity = (
        payload.get("from")
        or payload.get("user")
        or payload.get("username")
        or payload.get("igHandle")
        or thread
    )
    recent_orders = _safe_recent_orders(ctx) if etype == "dm" else None
    profile = _maybe_upsert_profile(ctx, "instagram", identity, payload, recent_orders)
    if profile and etype == "dm" and is_greeting(body):
        proposal = propose_reorder(profile)
        if proposal:
            ctx.evidence.write(
                "repeat_customer_detected",
                channel="instagram",
                sender=str(identity),
                threadId=thread,
                favoriteSku=proposal["sku"],
                priorOrders=proposal["count"],
                evidenceSources=["customer_profile", "square_recent_orders"],
            )
            _send_proposed_reorder(ctx, recipient=thread or identity, proposal=proposal, channel="instagram")
            return

    if ctx.sales_runner is None:
        ctx.evidence.write(
            "channel_dropped",
            channel="instagram",
            reason="sales_runner_not_configured",
        )
        return

    prompt = (
        f"An Instagram {etype} arrived for HappyCake US.\n\n"
        f"Thread: {thread}\n"
        f"From: {sender}\n"
        f"Message: {body}\n\n"
        "Use the happycake MCP. Reply via instagram_send_dm or "
        "instagram_reply_to_comment as appropriate. If the customer expresses "
        "order intent, route them to WhatsApp for confirmation (we centralize "
        "order intake there). Voice: warm, confident, ends with a clear next "
        "step."
    )
    ctx.sales_runner.run(prompt, label=f"instagram_{etype}")
