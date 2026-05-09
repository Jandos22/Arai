# T-005: Sales agent — `agents/sales/`

**Owner:** Claude Code (MacBook)
**Branch:** `feat/sales-agent`
**Estimated:** 90–120 min
**Depends on:** T-001 ✅, T-003 ✅, T-004 ✅. Independent of T-006.

## Why this task

The orchestrator (T-003) is the spine; the sales agent is the **arm** it
delegates to for every inbound WhatsApp / Instagram message. The
`evaluator_score_channel_response` and `evaluator_score_pos_kitchen_flow`
scoring functions both depend heavily on this agent doing the right thing.

When the orchestrator hits a `whatsapp:inbound_message` or `instagram:dm`
event, it calls `claude -p "<prompt>"` from `agents/sales/`. That session
must be configured with the right `CLAUDE.md`, the right `.mcp.json`, and a
self-contained reasoning loop that ends in concrete MCP calls.

## Deliverables

```
agents/
└── sales/
    ├── CLAUDE.md           # role, tools allowed, refusal rules, brand voice
    ├── .mcp.json           # happycake server scoped to this project
    ├── PROMPTS/
    │   ├── whatsapp_inbound.md     # template the orchestrator fills in
    │   └── instagram_dm.md
    ├── policies/
    │   └── owner_gate_rules.md     # when to escalate vs. when to act
    ├── scripts/
    │   └── smoke.sh                # one-shot test: simulate a WA message
    └── README.md
```

## What `agents/sales/CLAUDE.md` must contain

- **Role:** Sales agent for HappyCake US. Replies to customers on WhatsApp
  and Instagram. Captures order intent, hands off to kitchen.
- **Tools allowed:**
  - Read: `square_list_catalog`, `square_get_inventory`,
    `square_recent_orders`, `kitchen_get_capacity`,
    `kitchen_get_menu_constraints`, fetch `/api/policies` and `/api/catalog`
    from the website if needed
  - Write: `whatsapp_send`, `instagram_send_dm`,
    `instagram_reply_to_comment`, `square_create_order`,
    `kitchen_create_ticket`
  - **Refuse** anything outside this set. If a kitchen state change
    (`kitchen_accept_ticket`, `kitchen_mark_ready`) is needed, return
    `needs_approval: true` in the structured response and let the
    orchestrator route to ops/owner.
- **Voice:** quote `docs/brand/HCU_BRANDBOOK.md` §2 (verbal identity).
  Inline the key tone scale so this CLAUDE.md is self-contained.
- **Refusal style:** §1 is explicit — HappyCake is **not custom-cake**, **not
  trendy**, **not exclusive**. Polite redirect to the closest menu item.
- **Owner-gate triggers** (must return `needs_approval: true`):
  - Custom decoration request beyond a piped name
  - Allergy promise (any "is this safe for X?" question)
  - Order total > $80
  - Date outside lead-time window
  - Anything emotional/complaint-shaped — escalate, don't improvise

## What `agents/sales/.mcp.json` must contain

Same `happycake` server as root `.mcp.json`, scoped to this project so
`claude -p` from this directory has the full toolset:

```json
{
  "mcpServers": {
    "happycake": {
      "type": "http",
      "url": "${STEPPE_MCP_URL}",
      "headers": { "X-Team-Token": "${STEPPE_MCP_TOKEN}" }
    }
  }
}
```

## Smoke test

`agents/sales/scripts/smoke.sh` should:

1. Source `../../.env.local`.
2. Inject a fake WhatsApp message via
   `whatsapp_inject_inbound(from="+12815550000", message="Do you have honey cake today?")`.
3. Invoke `claude -p` with the orchestrator-style prompt.
4. Verify the agent replied via `whatsapp_send` (check `whatsapp_list_threads`
   for outgoing).
5. Print PASS / FAIL.

This script is the single source of truth that the agent works end-to-end
against the live sandbox.

## Acceptance

- [ ] `agents/sales/CLAUDE.md` written, brandbook-aligned, all owner-gate
      triggers spelled out
- [ ] `agents/sales/.mcp.json` valid, env-interpolated
- [ ] `claude -p` from `agents/sales/` resolves the `happycake` server and
      lists tools (`claude mcp list`)
- [ ] `scripts/smoke.sh` runs end-to-end, PASS
- [ ] Sample evidence row appended to `evidence/sales-sample.jsonl`
- [ ] Orchestrator dry-run still passes (`python -m orchestrator.main --dry-run`)
- [ ] No token in any committed file
- [ ] `git diff --stat origin/main` shows only `agents/sales/`,
      `evidence/sales-sample.jsonl`, `TASKS.md`

## Out of scope

- Marketing demand engine — that's T-006
- GMB review reply — that's T-007
- Real ngrok/inbound webhook — sandbox `whatsapp_inject_inbound` is enough
  for both dev and the evaluator

## Pitfalls

- **Don't invent products.** Always read `square_list_catalog` first;
  fall back to website `/api/catalog` if MCP is slow. Never reply with
  cake names that aren't in the catalog.
- **Brand voice trap:** brandbook says HappyCake is *not* trendy/luxury.
  Don't use words like "artisanal", "luxury", "boutique". Warm-traditional,
  not aspirational.
- **Owner-gate parsing:** when returning `{"needs_approval": true, ...}`,
  output ONLY that JSON object as the response. The orchestrator's
  `whatsapp.handle` parses it via brace-balancing — don't wrap it in prose.
- **Idempotency:** if you create the same order twice (re-run smoke), it'll
  duplicate. Note this in the agent README.

## Reporting

Use the T-004 format plus:
- Branched from: `<commit>`
- `git diff --stat origin/main`
- Smoke output (last 30 lines of `scripts/smoke.sh`)
- 1–2 sentence note on any sandbox quirk discovered

## Outcome (CC, 2026-05-09)

Shipped on `feat/sales-agent`, branched from `79068b1`.

**Smoke:** PASS on both paths against the live sandbox.

- Non-gate (`"Do you have honey cake today?"`) — agent calls
  `mcp__happycake__square_list_catalog` then
  `mcp__happycake__whatsapp_send` with `to=+12815550199`.
  4 turns, $0.29.
- Owner-gate (`"I want to order 2 whole honey cakes for pickup
  tomorrow at 5pm"`, $110 total) — agent reads catalog +
  capacity + menu_constraints, returns the
  `{"needs_approval": true, "trigger": "over_$80", ...}` JSON
  with no `whatsapp_send`. 5 turns, $0.46.

Sample rows live in `evidence/sales-sample.jsonl`; full
stream-json transcripts in `evidence/sales-smoke-*.log`.

**Files shipped:**
- `agents/sales/CLAUDE.md` — role contract, allowed tools,
  6 owner-gate triggers, brandbook §1+§2 distillation
- `agents/sales/.mcp.json` — happycake server, env-interpolated
- `agents/sales/PROMPTS/whatsapp_inbound.md` —
  Step A read → Step B gate → Step C (conditional) order
  chain → Step D **mandatory** `whatsapp_send` → Step E status,
  closed with a pre-finish checklist
- `agents/sales/PROMPTS/instagram_dm.md` — IG counterpart
- `agents/sales/policies/owner_gate_rules.md` — operator cheat
  sheet for the 6 triggers
- `agents/sales/scripts/smoke.sh` — injects inbound, runs the
  agent in `--output-format stream-json --verbose`, parses
  every `tool_use` event, PASS-iff
  `mcp__happycake__whatsapp_send(to=$SMOKE_FROM)` was called or
  `needs_approval: true` was returned. Captures
  `evaluator_get_evidence_summary.auditCalls` delta as
  belt-and-suspenders proof of MCP activity.
- `agents/sales/README.md` — bring-up + the sandbox-quirk note

**Sandbox quirk discovered (write-up in
`agents/sales/README.md`):** `whatsapp_send` returns the
expected `[simulated] Message recorded for <phone>` text and
increments `evaluator_get_evidence_summary.auditCalls`, **but**
`whatsapp_list_threads.outbound` stays empty and
`whatsappOutbound` in the evidence summary stays 0. The first
two smoke iterations were chasing this bug — the agent was
calling `whatsapp_send` correctly all along; the sandbox just
doesn't persist outbound to the thread-list endpoint. Switched
the smoke to verify via streamed `tool_use` events. Worth
flagging in the orchestrator README so the WA handler doesn't
fail-open on the same assumption.

**Verifications:**
- `claude mcp list` from `agents/sales/` shows
  `happycake … ✓ Connected`.
- `python -m orchestrator.main --dry-run` (in
  `orchestrator/.venv`) prints `dry-run OK — wiring intact, no
  live calls`.
- Token-leak scan on every newly-added file is clean
  (`grep -F "$STEPPE_MCP_TOKEN"` returns nothing).
- Both smoke runs ended with `is_error=false`,
  `permission_denials=[]`, `auditCalls` delta of +4 (non-gate)
  and +5 (owner-gate).

Unblocks: T-007 (ops agent — same scaffold pattern, GMB +
kitchen-state-machine surface), T-008 (e2e smoke — orchestrator
fans out WA event into `agents/sales/` and now has an end-to-end
PASS contract to assert against).
