# `agents/ops/` — Ops Agent

Self-contained Claude Code project that the orchestrator (T-003) shells
out to whenever:

- a Google Business review needs a reply,
- Google Business metrics, local posts, or Q&A/presence checks need a
  simulator-safe action,
- a kitchen / product trigger fires for an Instagram post,
- the Sales agent escalates a kitchen ticket the state machine has to move.

Builds on the MCP wiring from T-004 and the orchestrator hand-off shape
from T-005 (sales).

## What's in here

```
agents/ops/
├── CLAUDE.md                # role contract: tools, voice, owner-gate triggers
├── .mcp.json                # happycake MCP, env-interpolated token
├── PROMPTS/
│   ├── gmb_review.md            # template — review reply
│   ├── gmb_local_presence.md    # template — metrics, proposed GMB posts, Q&A gap
│   ├── ig_post_proposal.md      # template — schedule → owner approve → publish
│   └── kitchen_state.md         # template — accept / reject / mark_ready
├── policies/
│   └── escalation_rules.md      # cheat sheet for when to escalate
├── scripts/
│   ├── smoke_gmb.sh             # end-to-end review-reply test
│   ├── smoke_gmb_local.sh       # metrics + proposed local-post test
│   └── smoke_ig_post.sh         # schedule → owner approve → publish test
└── README.md
```

## Run the smokes

```sh
# from repo root
bash agents/ops/scripts/smoke_gmb.sh
bash agents/ops/scripts/smoke_gmb_local.sh
bash agents/ops/scripts/smoke_ig_post.sh
```

Both scripts:

1. source `.env.local` for `STEPPE_MCP_URL` + `STEPPE_MCP_TOKEN`,
2. snapshot the sandbox audit-call counter via
   `evaluator_get_evidence_summary`,
3. run `claude -p` from this folder with the relevant prompt template
   in `--output-format stream-json --verbose` so we can capture every
   `tool_use` event,
4. verify the agent took the expected MCP action (or returned the
   owner-gate JSON, where applicable),
5. append one summary row to `evidence/ops-sample.jsonl`,
6. print `PASS` / `FAIL` with the matching tool payload.

## Smoke pass criteria

### `smoke_gmb.sh`

PASS when both:

- the agent's stream-json contained a `tool_use` for
  `mcp__happycake__gb_simulate_reply` (or the owner-gate JSON for a
  rating ≤ 2 review), and
- `auditCalls` from `evaluator_get_evidence_summary` incremented by ≥1
  across the run.

### `smoke_ig_post.sh`

PASS when all three:

1. **Stage 1 (propose)** — the agent's stream-json contained a
   `tool_use` for `mcp__happycake__instagram_schedule_post` and the
   final result is owner-gate JSON with `trigger="ig_post_publish"`
   and a non-empty `ref_id` (the `scheduledPostId`).
2. **Owner-approval simulation** — the harness directly calls
   `instagram_approve_post(scheduledPostId)` (in production this would
   be the Telegram inline-keyboard tap). Sandbox returns success.
3. **Stage 2 (publish)** — the agent's stream-json (second `claude -p`
   invocation) contained a `tool_use` for
   `mcp__happycake__instagram_publish_post` with the same
   `scheduledPostId`.

The IG post smoke is the **money shot** — it proves the canonical
owner-gate pattern works end-to-end. The orchestrator will eventually
replace step 2 with a real Telegram inline-keyboard callback; for now
the harness simulates it directly.

### `smoke_gmb_local.sh`

PASS when both:

- **Metrics stage** calls `gb_get_metrics` and
  `gb_list_simulated_actions`, then summarizes local search presence.
- **Post stage** calls `gb_simulate_post` and returns owner-gate JSON
  with `trigger="gmb_post_publish"` and `channel="gmb"`.

The smoke deliberately does not invent Google Business Q&A behavior:
the live simulator catalog has no `gb_*` Q&A read/write tool. The
prompt documents this as a gap and reports it instead of fabricating a
tool call.

## Idempotency

There's no upsert in the sandbox. Re-running the smokes adds new
review replies, new scheduled posts, and (after the second stage) new
published posts. That's intentional for the demo; the evaluator scores
the audit trail, not dedup behaviour.

## Sandbox quirks worth knowing

- **`gb_simulate_reply`** records the reply against the reviewId even
  if we've already replied; check `gb_list_simulated_actions` first to
  avoid double-replies.
- **`gb_simulate_post`** records a proposed Google Business post in the
  simulator. It is not a separate approve/publish state machine, so the
  agent returns owner-gate JSON after recording the proposal.
- **Google Business Q&A** is not exposed in the current live `gb_*`
  catalog. Treat Q&A requests as a documented simulator gap.
- **`instagram_publish_post`** errors hard if `instagram_approve_post`
  hasn't recorded approval for the same `scheduledPostId`. That
  hard-error is the safety net behind the canonical owner-gate
  pattern; rule #3 in `CLAUDE.md` exists to keep us from tripping it
  by accident.
- **`instagram_schedule_post`** does not validate `imageUrl`, but the
  field is required. Use a stable `https://happycake.us/...` path the
  owner would recognize.

## How the orchestrator drives this (eventual)

Per-event hand-off pattern, mirroring `agents/sales/`:

- GMB review → `orchestrator/handlers/gmb.py` builds the review prompt,
  calls `ctx.ops_runner.run(prompt, label="gmb_review")`, parses the
  response. Owner-gate JSON → Telegram inline keyboard. Plain stdout
  with a `gb_simulate_reply` `tool_use` → done.
- GMB local post / metrics / Q&A → `orchestrator/handlers/gmb.py`
  builds the local-presence prompt. Proposed posts call
  `gb_simulate_post` and return `gmb_post_publish` owner-gate JSON;
  metrics-only checks summarize; Q&A requests report the missing live
  tool.
- Kitchen / product trigger → `orchestrator/handlers/ig_post.py` (TODO)
  builds the prompt with `stage=propose`. Owner-gate JSON →
  Telegram inline keyboard. On owner Approve, the bot calls
  `instagram_approve_post` and re-invokes the agent with
  `stage=publish` and the `scheduledPostId`.
- Sales escalation of a kitchen ticket →
  `orchestrator/handlers/kitchen_state.py` (TODO).

The smokes here exercise the agent the same way the orchestrator
will, so the wiring is largely a matter of calling
`ops_runner.run(prompt, label=...)` and parsing the result with the
existing `_extract_json`.

## Tools allowed (single responsibility)

The full list is in `CLAUDE.md`. Headline:

- **GMB**: `gb_list_reviews`, `gb_simulate_reply`, `gb_simulate_post`,
  `gb_get_metrics`, `gb_list_simulated_actions`.
- **Instagram (post side only)**: `instagram_schedule_post`,
  `instagram_approve_post`, `instagram_publish_post`,
  `instagram_register_webhook`.
- **Kitchen**: `kitchen_get_capacity`, `kitchen_get_menu_constraints`,
  `kitchen_list_tickets`, `kitchen_accept_ticket`,
  `kitchen_reject_ticket`, `kitchen_mark_ready`,
  `kitchen_get_production_summary`.
- **Refused**: `whatsapp_*`, `instagram_send_dm`,
  `instagram_reply_to_comment`, `square_create_order`,
  `square_update_order_status`, `kitchen_create_ticket`,
  everything in the `marketing_*`, `world_*`, `evaluator_*`
  namespaces. Sales / marketing / orchestrator territory.

## Owner-gate triggers (recap — see `policies/escalation_rules.md`)

| Trigger | Channel | When |
|---|---|---|
| `ig_post_publish` | instagram | Always — every IG publish goes through the owner. |
| `gmb_post_publish` | gmb | Any Google Business local post proposal after `gb_simulate_post`. |
| `kitchen_reject` | kitchen | Capacity / lead-time / inventory makes the promise unsafe. |
| `kitchen_terminal_state` | kitchen | Ticket already `completed` / `rejected` / `cancelled`. |
| `review_low_rating` | gmb | GMB review with `rating ≤ 2`. |
| `review_refund_offer` | gmb | Draft reply contains refund / replacement / money. |
