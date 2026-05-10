# Prompt template — Google Business local presence

> The orchestrator (or `scripts/smoke_gmb_local.sh`) fills `{{mode}}`,
> `{{trigger}}`, and `{{trigger_detail}}` before piping this to
> `claude -p` from `agents/ops/`. Read `CLAUDE.md` in this folder for
> the role contract; this prompt is the per-event procedure.

---

A Google Business local-presence trigger fired for HappyCake.

Mode: {{mode}}
Trigger: {{trigger}}
Trigger detail: {{trigger_detail}}

## Available simulator surface

The current live `gb_*` catalog is:

- `gb_list_reviews`
- `gb_simulate_reply`
- `gb_simulate_post`
- `gb_get_metrics`
- `gb_list_simulated_actions`

There is no Google Business Q&A tool in the live catalog. If the trigger
asks for Q&A, do not invent a tool. Report the gap in final stdout and,
if useful, recommend a manually approved owner response outside the
sandbox.

## Procedure — `mode=metrics`

1. Call `gb_get_metrics` with `{"period":"last_7_days"}`.
2. Call `gb_get_metrics` with `{"period":"last_30_days"}`.
3. Call `gb_list_simulated_actions`.
4. Return one short operational paragraph covering views, calls,
   direction requests, any recent simulated GMB actions, and whether a
   post or review follow-up is recommended.

Do not call `gb_simulate_post` in metrics mode unless `{{trigger_detail}}`
explicitly asks for a local post.

## Procedure — `mode=post`

1. Call `gb_get_metrics` with `{"period":"last_7_days"}`.
2. Call `gb_list_simulated_actions` to avoid proposing duplicate local
   content.
3. Draft a factual Google Business post in HappyCake voice:
   - Use **HappyCake** exactly.
   - Cake names use the format cake "Honey", cake "Pistachio Roll".
   - Keep it to 1-3 short sentences.
   - Include concrete pickup, timing, or ordering details only if they
     appear in `{{trigger_detail}}`.
   - Use at most one soft call to action.
   - Never invent prices, inventory, allergens, hours, or delivery.
4. Call `gb_simulate_post` exactly once:

```
mcp__happycake__gb_simulate_post({
  content: "<the exact post text>",
  callToAction: {"label": "Order", "url": "https://happycake.us/order"}
})
```

Use `photoUrl` only if `{{trigger_detail}}` provides a stable image URL.

5. Return only this owner-gate JSON object:

```json
{
  "needs_approval": true,
  "summary": "<2-3 sentences for the owner: why this GMB post is being proposed and what local signal triggered it>",
  "draft": "<the exact post text passed to gb_simulate_post>",
  "trigger": "gmb_post_publish",
  "channel": "gmb",
  "ref_id": "<simulated action id if returned, otherwise {{trigger}}>"
}
```

No prose before or after. `gb_simulate_post` records a proposed sandbox
action only; do not claim a real Google Business post was published.

## Procedure — `mode=q_and_a`

1. Call `gb_list_simulated_actions`.
2. Return one short paragraph stating that the live simulator has no
   Q&A read/write tool, so no Q&A tool call was made. Include the
   owner-readable answer draft only if `{{trigger_detail}}` includes a
   concrete question.

## Hard rules

- Never echo `STEPPE_MCP_TOKEN` or any auth header.
- Never call non-GMB tools from this prompt.
- Public-facing GMB post content must end in the `gmb_post_publish`
  owner-gate JSON.
- If any checklist item below is unchecked, fix it before finishing.

## Pre-finish checklist

If `mode=metrics`:

- [ ] I called both `gb_get_metrics` periods.
- [ ] I called `gb_list_simulated_actions`.
- [ ] I did not invent Q&A tooling.

If `mode=post`:

- [ ] I called `gb_get_metrics` for `last_7_days`.
- [ ] I called `gb_list_simulated_actions`.
- [ ] I called `gb_simulate_post` exactly once.
- [ ] My final stdout is only owner-gate JSON with
      `trigger="gmb_post_publish"`.

If `mode=q_and_a`:

- [ ] I stated that no live `gb_*` Q&A tool exists.
- [ ] I did not invent a Q&A tool call.

Begin now.
