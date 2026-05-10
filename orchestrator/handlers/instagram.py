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
from .whatsapp import (
    _extract_json,
    _maybe_upsert_profile,
    _queue_owner_gated_draft,
    _safe_recent_orders,
    _send_proposed_reorder,
)


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
        "step. If the request needs owner approval (custom decoration, allergy "
        "promise, order > $80, standing order), do NOT call an Instagram send "
        "tool — return a JSON object {\"needs_approval\": true, \"summary\": "
        "\"...\", \"draft_reply\": \"...\"} and the orchestrator will route it "
        "to the owner."
    )
    response = ctx.sales_runner.run(prompt, label=f"instagram_{etype}")

    if "needs_approval" not in response:
        lowered = response.lower()
        if not (thread or comment_id) or "draft" in lowered or "can't" in lowered or "cannot" in lowered:
            _queue_instagram_response_draft(
                ctx,
                etype=etype,
                thread=thread,
                comment_id=comment_id,
                identity=identity,
                body=response,
            )
        return
    try:
        decoded = json.loads(_extract_json(response))
    except (ValueError, json.JSONDecodeError):
        _queue_instagram_response_draft(
            ctx,
            etype=etype,
            thread=thread,
            comment_id=comment_id,
            identity=identity,
            body=response,
            parse_failed=True,
        )
        return
    if not decoded.get("needs_approval"):
        return

    draft_reply = decoded.get("draft_reply", "")
    recipient = thread or identity
    tool = "instagram_reply_to_comment" if comment_id else "instagram_send_dm"
    recipient_key = "commentId" if comment_id else "threadId"
    _queue_owner_gated_draft(
        ctx,
        label=f"instagram_{etype}_owner_gate_draft",
        channel="instagram",
        tool=tool,
        recipient_key=recipient_key,
        recipient=comment_id or recipient,
        body=draft_reply,
        reason=decoded.get("trigger") or decoded.get("kind", "transactional"),
    )

    if ctx.telegram_notifier is None:
        return
    ctx.telegram_notifier.request_approval(
        summary=decoded.get("summary", "Pending Instagram action"),
        draft=draft_reply,
        context={
            "channel": "instagram",
            "subtype": etype,
            "sender": sender,
            "threadId": thread,
            "commentId": comment_id,
            "body": body,
            "kind": decoded.get("kind", "transactional"),
            "trigger": decoded.get("trigger"),
            "request_details": decoded.get("request_details"),
            "proposed_resolution": decoded.get("proposed_resolution"),
            "remediation_tool_chain": decoded.get("remediation_tool_chain"),
        },
    )


def _queue_instagram_response_draft(
    ctx: HandlerContext,
    *,
    etype: str,
    thread: Any,
    comment_id: Any,
    identity: Any,
    body: str,
    parse_failed: bool = False,
) -> None:
    if not body.strip():
        return
    tool = "instagram_reply_to_comment" if etype == "comment" else "instagram_send_dm"
    recipient_key = "commentId" if etype == "comment" else "threadId"
    recipient = comment_id if etype == "comment" else thread
    status = "draft_ready" if recipient else "draft_needs_recipient"
    reason = None if recipient else "missing_comment_or_thread_id"
    _queue_owner_gated_draft(
        ctx,
        label=f"instagram_{etype}_draft",
        channel="instagram",
        tool=tool,
        recipient_key=recipient_key,
        recipient=recipient or identity or "unknown",
        body=body,
        reason=reason,
        status=status,
    )
    ctx.evidence.write(
        "instagram_draft_queued",
        subtype=etype,
        status=status,
        parseFailed=parse_failed,
        recipientKey=recipient_key,
        recipient=recipient or identity or "unknown",
        bodyPreview=body[:240],
        evidenceSources=["instagram_inbound", tool],
    )
