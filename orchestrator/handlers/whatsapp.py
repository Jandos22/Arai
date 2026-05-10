"""WhatsApp inbound handler.

Wraps the inbound message into a structured prompt for the sales agent
and shells out to ``claude -p`` in ``agents/sales/``. The sales agent
itself decides which MCP tools to call (catalog, inventory, send reply,
create order, kitchen ticket).
"""
from __future__ import annotations

import json
from typing import Any

from ..dispatcher import HandlerContext
from ..growth import build_pickup_follow_up_message, score_whatsapp_lead


def handle(event: dict[str, Any], ctx: HandlerContext) -> None:
    payload = event.get("payload") or event
    sender = payload.get("from") or payload.get("phone")
    body = payload.get("message") or payload.get("text") or ""

    ctx.evidence.write(
        "channel_inbound",
        channel="whatsapp",
        sender=sender,
        bodyPreview=body[:200],
    )

    recent_orders = _safe_recent_orders(ctx)
    lead_score = score_whatsapp_lead(payload, recent_orders)
    ctx.evidence.write(
        "lead_score",
        channel="whatsapp",
        sender=sender,
        score=lead_score.score,
        segment=lead_score.segment,
        route=lead_score.route,
        followUpAfterMinutes=lead_score.follow_up_after_minutes,
        reasons=lead_score.reasons,
        evidenceSources=["whatsapp_inbound", "square_recent_orders"],
    )

    if ctx.sales_runner is None:
        ctx.evidence.write(
            "channel_dropped",
            channel="whatsapp",
            reason="sales_runner_not_configured",
        )
        return

    prompt = (
        "A customer just messaged HappyCake US on WhatsApp.\n\n"
        f"From: {sender}\n"
        f"Message: {body}\n\n"
        "Use the happycake MCP. Read catalog and policies if needed, then "
        "answer in HappyCake brand voice (warm, confident, ends with a clear "
        "next step). If the customer expresses order intent, capture it via "
        "square_create_order then kitchen_create_ticket. Reply via whatsapp_send. "
        "If the request needs owner approval (custom decoration, allergy "
        "promise, order > $80), do NOT call whatsapp_send — return a JSON "
        "object {\"needs_approval\": true, \"summary\": \"...\", \"draft_reply\": \"...\"} "
        "and the orchestrator will route it to the owner."
    )
    response = ctx.sales_runner.run(prompt, label="whatsapp_inbound")

    # Best-effort: detect approval-gated responses and forward to Telegram.
    if ctx.telegram_notifier is not None and "needs_approval" in response:
        try:
            decoded = json.loads(_extract_json(response))
            if decoded.get("needs_approval"):
                kind = decoded.get("kind", "transactional")
                severity = decoded.get("severity")
                summary = decoded.get("summary", "Pending action")
                # Prefix the summary so it surfaces clearly in Telegram for
                # the new T-013 paths (complaint with allergy, custom-cake quote).
                tagged_summary = summary
                if kind == "complaint":
                    sev = (severity or "medium").upper()
                    tagged_summary = f"[COMPLAINT · {sev}] {summary}"
                elif kind == "custom_cake_consult":
                    tagged_summary = f"[CUSTOM CAKE] {summary}"
                ctx.telegram_notifier.request_approval(
                    summary=tagged_summary,
                    draft=decoded.get("draft_reply", ""),
                    context={
                        "channel": "whatsapp",
                        "sender": sender,
                        "body": body,
                        "kind": kind,
                        "severity": severity,
                        "proposed_resolution": decoded.get("proposed_resolution"),
                        "remediation_tool_chain": decoded.get("remediation_tool_chain"),
                        "request_details": decoded.get("request_details"),
                        "kitchen_constraints": decoded.get("kitchen_constraints"),
                        "trigger": decoded.get("trigger"),
                    },
                )
        except (ValueError, json.JSONDecodeError):
            ctx.evidence.write(
                "approval_parse_failed",
                channel="whatsapp",
                responsePreview=response[:200],
            )


def handle_follow_up_due(event: dict[str, Any], ctx: HandlerContext) -> None:
    """Send a scheduled WhatsApp pickup follow-up after checking Square."""
    payload = event.get("payload") or event
    recipient = payload.get("to") or payload.get("from") or payload.get("phone")
    if not recipient:
        ctx.evidence.write("whatsapp_follow_up_skipped", reason="missing_recipient", payload=payload)
        return

    recent_orders = _safe_recent_orders(ctx)
    message = payload.get("message") or build_pickup_follow_up_message(payload, recent_orders)
    args = {"to": recipient, "message": message}
    try:
        result = ctx.client.call_tool("whatsapp_send", args)
    except Exception as exc:  # noqa: BLE001
        ctx.evidence.mcp_call("whatsapp_send", args=args, ok=False, error=str(exc))
        ctx.evidence.write(
            "whatsapp_follow_up_failed",
            recipient=recipient,
            error=str(exc),
            evidenceSources=["square_recent_orders", "whatsapp_send"],
        )
        return

    ctx.evidence.mcp_call("whatsapp_send", args=args, result_summary=result)
    ctx.evidence.write(
        "whatsapp_follow_up_sent",
        recipient=recipient,
        bodyPreview=str(message)[:240],
        evidenceSources=["square_recent_orders", "whatsapp_send"],
    )
    ctx.evidence.write(
        "channel_outbound",
        label="whatsapp_follow_up",
        channel="whatsapp",
        tool="whatsapp_send",
        recipientKey="to",
        recipient=recipient,
        bodyPreview=str(message)[:240],
    )


def _safe_recent_orders(ctx: HandlerContext) -> Any:
    try:
        result = ctx.client.call_tool("square_recent_orders", {})
    except Exception as exc:  # noqa: BLE001
        ctx.evidence.mcp_call("square_recent_orders", args={}, ok=False, error=str(exc))
        return None
    ctx.evidence.mcp_call("square_recent_orders", args={}, result_summary=result)
    return result


def _extract_json(text: str) -> str:
    """Pull the first balanced ``{...}`` block out of a model response."""
    start = text.find("{")
    if start == -1:
        return text
    depth = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text
