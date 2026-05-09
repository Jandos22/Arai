# `agents/sales/` — Sales Agent

Self-contained Claude Code project that the orchestrator (T-003) shells
out to whenever an inbound WhatsApp message or Instagram DM hits the
sandbox. Builds on the MCP wiring from T-004.

## What's in here

```
agents/sales/
├── CLAUDE.md            # role contract: tools, voice, owner-gate triggers
├── .mcp.json            # happycake MCP, env-interpolated token
├── PROMPTS/
│   ├── whatsapp_inbound.md   # template the orchestrator fills (from, message)
│   └── instagram_dm.md       # IG counterpart (thread_id, from, message)
├── policies/
│   └── owner_gate_rules.md   # cheat sheet for when to escalate
├── scripts/
│   └── smoke.sh         # end-to-end test against whatsapp_inject_inbound
└── README.md
```

## Run the smoke

```sh
# from repo root
bash agents/sales/scripts/smoke.sh
# or with a custom message
bash agents/sales/scripts/smoke.sh "Two pistachio rolls for pickup at 5pm?"
```

The script:

1. sources `.env.local` for `STEPPE_MCP_URL` + `STEPPE_MCP_TOKEN`,
2. injects an inbound WhatsApp message from `+12815550199`,
3. runs `claude -p` from this folder with `PROMPTS/whatsapp_inbound.md`
   filled in,
4. polls `whatsapp_list_threads` for up to 30s for a matching outbound
   reply (or detects the owner-gate JSON path),
5. appends one summary row to `evidence/sales-sample.jsonl`,
6. prints `PASS` / `FAIL` with the matching outbound payload.

## Smoke pass criteria

The smoke prints **PASS** when either:

- `whatsapp_list_threads` shows a non-empty outbound message addressed
  to the smoke phone (`+12815550199`); **or**
- the agent's stdout contains `"needs_approval": true` (the owner-gate
  path, which intentionally does not call `whatsapp_send`).

Both are valid sales-agent outcomes. The default smoke message
("Do you have honey cake today?") is well below all owner-gate
thresholds, so it should land in the first bucket.

## Idempotency

There is no upsert in the sandbox — each smoke run creates a brand-new
order and kitchen ticket if the agent decides to act on the message.
Re-running the script will accumulate orders/tickets in the simulator.
That's intentional for the demo; the evaluator scores the audit trail,
not the dedup behaviour.

## Sandbox quirks discovered

- **`whatsapp_send` doesn't populate `whatsapp_list_threads.outbound`.**
  The call returns the expected `[simulated] Message recorded for
  <phone>. <n> chars. Real WhatsApp delivery activates once Meta
  credentials are wired.` text and increments
  `evaluator_get_evidence_summary.counts.auditCalls`, but
  `whatsapp_list_threads.outbound` stays `[]` and
  `evaluator_get_evidence_summary.counts.whatsappOutbound` stays `0`.
  Confirmed by curl too — not an agent bug. The smoke verifies
  outbound by parsing streamed `tool_use` events from
  `claude -p --output-format stream-json --verbose`, not by polling
  the thread list. Worth flagging when wiring up
  `orchestrator/handlers/whatsapp.py` — the orchestrator should not
  rely on `whatsapp_list_threads.outbound` to confirm a reply landed.
- `whatsapp_inject_inbound` returns an empty body on success
  (`result.content[0].text` is the empty string). The injection is
  visible by calling `whatsapp_list_threads` afterwards.
- `whatsapp_list_threads.inbound` is cumulative across the team's
  session — old inbound entries persist across smoke runs.

## How the orchestrator drives this

`orchestrator/handlers/whatsapp.py` builds the prompt from the inbound
event, calls `ctx.sales_runner.run(prompt, label="whatsapp_inbound")`
(which `cd`s into this folder and runs `claude -p`), then parses the
agent's response. If the response contains `"needs_approval": true`,
the orchestrator's `_extract_json` walks the first balanced `{...}`
block and forwards `summary` + `draft_reply` to the owner via Telegram
inline-keyboard approval.

## Tools allowed (single responsibility)

The full list is in `CLAUDE.md`. Headline:

- **Read**: `square_list_catalog`, `square_get_inventory`,
  `square_recent_orders`, `kitchen_get_capacity`,
  `kitchen_get_menu_constraints`, `whatsapp_list_threads`,
  `instagram_list_dm_threads`.
- **Write**: `whatsapp_send`, `instagram_send_dm`,
  `instagram_reply_to_comment`, `square_create_order`,
  `kitchen_create_ticket`.
- **Refused**: kitchen state-machine moves
  (`kitchen_accept_ticket`/`reject_ticket`/`mark_ready`),
  `square_update_order_status`, IG post scheduling/publishing,
  everything in the `marketing_*`, `gb_*`, `world_*`, `evaluator_*`
  namespaces. Those are sibling agents (ops, marketing) or orchestrator
  responsibilities.

## Owner-gate triggers (recap — see `policies/owner_gate_rules.md`)

1. Custom decoration beyond a piped name.
2. Allergy promise.
3. Order total > $80.
4. Date inside a product's `leadTimeMinutes`.
5. Anything emotional or complaint-shaped.
6. Any line item with `requiresCustomWork: true`.

When a trigger fires, the agent returns:

```json
{
  "needs_approval": true,
  "summary": "...",
  "draft_reply": "...",
  "trigger": "...",
  "channel": "whatsapp" | "instagram",
  "to": "..."
}
```

…and stops. The orchestrator routes it to the owner.
