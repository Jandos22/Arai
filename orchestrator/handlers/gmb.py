"""Google Business handler — review replies + scheduled posts."""
from __future__ import annotations

from typing import Any

from ..dispatcher import HandlerContext


def handle(event: dict[str, Any], ctx: HandlerContext) -> None:
    payload = event.get("payload") or event
    etype = event.get("type", "review")

    ctx.evidence.write(
        "channel_inbound",
        channel="gmb",
        subtype=etype,
        payloadPreview={k: payload.get(k) for k in ("reviewId", "rating", "text") if k in payload},
    )

    if ctx.ops_runner is None:
        ctx.evidence.write(
            "channel_dropped",
            channel="gmb",
            reason="ops_runner_not_configured",
        )
        return

    if etype == "review_received":
        prompt = (
            "A new Google Business review arrived for HappyCake US.\n\n"
            f"Review payload: {payload}\n\n"
            "Read the review with gb_list_reviews if you need full context, "
            "then draft a reply with gb_simulate_reply. The reply must follow "
            "brandbook §6: open dialogue, never delete or argue, always offer "
            "a next step (DM us, come back, etc.). For 1-2 star reviews, also "
            "log a follow-up via the orchestrator approval flow."
        )
    else:
        prompt = (
            f"A Google Business event arrived: {etype}.\n\n"
            f"Payload: {payload}\n\n"
            "Decide whether action is needed. Tools: gb_list_reviews, "
            "gb_simulate_reply, gb_simulate_post, gb_get_metrics."
        )
    ctx.ops_runner.run(prompt, label=f"gmb_{etype}")
