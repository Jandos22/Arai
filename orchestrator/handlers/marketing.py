"""Marketing trigger — "owner asked for a campaign" or scheduled tick."""
from __future__ import annotations

from typing import Any

from ..dispatcher import HandlerContext


def handle(event: dict[str, Any], ctx: HandlerContext) -> None:
    payload = event.get("payload") or event
    ctx.evidence.write("channel_inbound", channel="marketing", payload=payload)

    if ctx.marketing_runner is None:
        ctx.evidence.write(
            "channel_dropped",
            channel="marketing",
            reason="marketing_runner_not_configured",
        )
        return

    prompt = (
        "Marketing trigger received.\n\n"
        f"Payload: {payload}\n\n"
        "Run the demand-engine chain end-to-end against the happycake MCP: "
        "marketing_get_budget, marketing_get_sales_history, "
        "marketing_get_margin_by_product → marketing_create_campaign → "
        "marketing_launch_simulated_campaign → marketing_generate_leads → "
        "marketing_route_lead → marketing_adjust_campaign → marketing_report_to_owner. "
        "Cite the data you used. End with the report-to-owner summary."
    )
    ctx.marketing_runner.run(prompt, label="marketing_trigger")
