"""Google Business handler — reviews, local posts, metrics, and presence."""
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

    prompt, label = _prompt_for(etype, payload)
    ctx.ops_runner.run(prompt, label=label)


def _prompt_for(etype: str, payload: dict[str, Any]) -> tuple[str, str]:
    if etype in {"review_received", "review"}:
        return _review_prompt(payload), "gmb_review"

    if etype in {"local_post_request", "post_request", "daily_post", "presence_post"}:
        return _local_post_prompt(etype, payload), "gmb_local_post"

    if etype in {"metrics_check", "local_metrics", "presence_check", "q_and_a"}:
        return _presence_prompt(etype, payload), "gmb_presence"

    return _presence_prompt(etype, payload), f"gmb_{etype}"


def _review_prompt(payload: dict[str, Any]) -> str:
    return (
        "A new Google Business review arrived for HappyCake US.\n\n"
        f"Review payload: {payload}\n\n"
        "Read the review with gb_list_reviews and check gb_list_simulated_actions "
        "before drafting so we do not double-reply. If the rating is 1-2 stars, "
        "or if the draft includes a refund, replacement, or monetary offer, "
        "return only the owner-gate JSON from agents/ops/CLAUDE.md and do not "
        "call gb_simulate_reply. Otherwise draft a reply with gb_simulate_reply. "
        "The reply must follow brandbook section 6: open dialogue, never delete "
        "or argue, answer in English, sign as people, and always offer a clear "
        "next step."
    )


def _local_post_prompt(etype: str, payload: dict[str, Any]) -> str:
    return (
        f"A Google Business local-post trigger arrived: {etype}.\n\n"
        f"Payload: {payload}\n\n"
        "Use the GMB local-presence procedure. Read gb_get_metrics for "
        "last_7_days and gb_list_simulated_actions before drafting. If a post "
        "is useful, call gb_simulate_post exactly once to record the proposed "
        "Google Business post. Because this is public-facing local content, "
        "your final stdout must be only an owner-gate JSON object with "
        'trigger=\"gmb_post_publish\", channel=\"gmb\", draft set to the exact '
        "post text, and ref_id set to the simulated action id if the tool "
        "returns one; use the event type if no id is returned. Do not claim a "
        "real Google Business post was published."
    )


def _presence_prompt(etype: str, payload: dict[str, Any]) -> str:
    return (
        f"A Google Business local-presence event arrived: {etype}.\n\n"
        f"Payload: {payload}\n\n"
        "Audit the available gb_* simulator state using gb_list_reviews, "
        "gb_get_metrics, and gb_list_simulated_actions. The live tool catalog "
        "does not expose a Google Business Q&A write/read tool, so if the event "
        "asks for Q&A, report that gap clearly and do not invent a tool call. "
        "For review replies use gb_simulate_reply with the review owner gates. "
        "For proposed public local posts use gb_simulate_post and return the "
        "gmb_post_publish owner-gate JSON. For metrics-only checks, return a "
        "short operational summary with views, calls, direction requests, and "
        "whether a local post or review follow-up is recommended."
    )
