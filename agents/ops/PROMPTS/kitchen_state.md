# Prompt template — Kitchen state transition

> The orchestrator (or `scripts/smoke_kitchen.sh`, when wired) fills
> `{{ticket_id}}`, `{{requested_action}}`, and `{{context}}` before
> piping this to `claude -p` from `agents/ops/`. Read `CLAUDE.md` in
> this folder for the role contract; this prompt is the per-event
> procedure.

---

The Sales agent (or scenario loop) escalated a kitchen ticket to ops.
You decide whether to accept, reject, or mark ready — capacity-aware,
not just sequential.

Ticket ID: {{ticket_id}}
Requested action: {{requested_action}}   # one of: accept | reject | mark_ready
Context: {{context}}                     # free-text from the upstream
                                         # caller (Sales / orchestrator)

You will execute the procedure below. The customer is **not** reading
your final stdout — only your tool calls reach the kitchen simulator
and (via the orchestrator) the owner.

## Procedure

**Step A — Read inputs.** Call these in parallel:

- `mcp__happycake__kitchen_list_tickets` — find `{{ticket_id}}` and its
  current status. If the ticket isn't there, stop and return the no-op
  stdout described in Step E.
- `mcp__happycake__kitchen_get_capacity` — current `remainingCapacity
  Minutes`, `queuedTickets`, `acceptedTickets`. Drives the
  accept/reject decision.
- `mcp__happycake__kitchen_get_menu_constraints` — per-product
  `prepMinutes`, `leadTimeMinutes`, `requiresCustomWork`. Cross-check
  the ticket's items against capacity.

**Step B — Decide owner-gate.** Re-read `CLAUDE.md` triggers:

1. Is the requested action `reject` (regardless of reason)? → owner-
   gate. Surface the structured reason to the owner before calling
   `kitchen_reject_ticket`.
2. Is the ticket status already terminal (`completed`, `rejected`,
   `cancelled`)? → owner-gate, summary "ticket already terminal,
   confirm intent".

If ANY trigger fires → output ONLY the owner-gate JSON object as your
final response (no prose before, no prose after, no kitchen state
call):

```json
{
  "needs_approval": true,
  "summary": "...",
  "draft": "<one-sentence reason or status note for the owner>",
  "trigger": "kitchen_reject | kitchen_terminal_state",
  "channel": "kitchen",
  "ref_id": "{{ticket_id}}"
}
```

…and stop. Skip Step C and D.

**Step C — Cross-check capacity (accept path only).** If
`{{requested_action}}` is `accept`:

- Sum `prepMinutes × quantity` across the ticket's items.
- If that sum > `remainingCapacityMinutes` from
  `kitchen_get_capacity`, treat this as a *should-be-reject* and switch
  to the owner-gate path with `trigger="kitchen_reject"` and a draft
  reason like *Capacity is N minutes; this ticket needs M minutes*.
- If `requiresCustomWork: true` on any item, that's an owner-gate
  trigger too — Sales should have caught it, but ops re-checks.

**Step D — Execute the requested action.** Whichever path you took,
call exactly one tool:

- `accept` (capacity OK, no custom work) →
  `mcp__happycake__kitchen_accept_ticket({ ticketId: "{{ticket_id}}" })`
- `mark_ready` →
  `mcp__happycake__kitchen_mark_ready({ ticketId: "{{ticket_id}}" })`
- `reject` is **never reached here** — it always goes through the
  owner-gate first. After the owner confirms, the orchestrator
  re-invokes you with the same prompt and `{{context}}` carrying the
  approval marker; on that turn you call
  `mcp__happycake__kitchen_reject_ticket({ ticketId: "{{ticket_id}}",
  reason: "<owner-confirmed reason>" })`.

**Step E — Final stdout.** After Step D returns successfully, output
one short paragraph (≤3 sentences) for the team channel describing:

- which ticket and which action you took,
- a one-line capacity / readiness note (e.g. *capacity 320/420 min
  remaining after accept*),
- whether anything in the production summary suggests a follow-up the
  owner should know about.

If Step A detected a missing ticket, your final stdout is one
sentence: *Ticket {{ticket_id}} not found in current queue; no action
taken.* No JSON, no kitchen state call.

Do **not** describe Step D as "I will accept" without having actually
called the kitchen tool.

## Hard rules (recap, see CLAUDE.md for full list)

- **Capacity before acceptance.** Always read capacity + constraints
  before calling `kitchen_accept_ticket`.
- **Reject always goes through the owner.** Never call
  `kitchen_reject_ticket` without the owner-gate path.
- Never call `kitchen_create_ticket` (Sales territory).
- Never echo `STEPPE_MCP_TOKEN` or any auth header.

## Pre-finish checklist

- [ ] I called `kitchen_list_tickets`, `kitchen_get_capacity`, and
      `kitchen_get_menu_constraints`.
- [ ] I evaluated both owner-gate triggers (reject path, terminal
      state) and the capacity cross-check.
- [ ] If any trigger fired, my final stdout is ONLY the owner-gate
      JSON object (and I skipped Step D).
- [ ] If the ticket was missing, my final stdout is the one-sentence
      no-op (and I skipped Step D).
- [ ] Otherwise I called exactly one of `kitchen_accept_ticket` /
      `kitchen_mark_ready` with `ticketId={{ticket_id}}`.

If any unchecked, fix it before finishing.

Begin now.
