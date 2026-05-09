"""WhatsApp inbound handler.

Wraps the inbound message into a structured prompt for the sales agent
and shells out to ``claude -p`` in ``agents/sales/``. The sales agent
itself decides which MCP tools to call (catalog, inventory, send reply,
create order, kitchen ticket).
"""
from __future__ import annotations

import json

from ..dispatcher import HandlerContext


def handle(event: dict[str, Any], ctx: HandlerContext) -> None:  # type: ignore[name-defined]
    payload = event.get("payload") or event
    sender = payload.get("from") or payload.get("phone")
    body = payload.get("message") or payload.get("text") or ""

    ctx.evidence.write(
        "channel_inbound",
        channel="whatsapp",
        sender=sender,
        bodyPreview=body[:200],
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
                ctx.telegram_notifier.request_approval(
                    summary=decoded.get("summary", "Pending action"),
                    draft=decoded.get("draft_reply", ""),
                    context={"channel": "whatsapp", "sender": sender, "body": body},
                )
        except (ValueError, json.JSONDecodeError):
            ctx.evidence.write(
                "approval_parse_failed",
                channel="whatsapp",
                responsePreview=response[:200],
            )


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
