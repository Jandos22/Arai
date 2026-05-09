"""Instagram DM/comment handler.

Same shape as WhatsApp: build prompt, delegate to sales agent. IG-specific:
post-publishing flow is owner-gated (schedule → owner approval via Telegram
→ ``instagram_publish_post``). Inbound handling here is just DM + comment.
"""
from __future__ import annotations

import json
from typing import Any

from ..dispatcher import HandlerContext


def handle(event: dict[str, Any], ctx: HandlerContext) -> None:
    payload = event.get("payload") or event
    thread = payload.get("threadId") or payload.get("thread")
    sender = payload.get("from") or "unknown"
    body = payload.get("message") or payload.get("text") or ""
    etype = event.get("type", "dm")

    ctx.evidence.write(
        "channel_inbound",
        channel="instagram",
        subtype=etype,
        threadId=thread,
        sender=sender,
        bodyPreview=body[:200],
    )

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
