# Escalation rules

> Operational checklist for the ops agent. The full rules and rationale
> live in `agents/ops/CLAUDE.md`. This file is the cheat sheet — when
> any row matches, the agent stops and returns the owner-gate JSON.

## What triggers the gate

| Trigger | What to look for | Why |
|---|---|---|
| **`ig_post_publish`** | Any `instagram_publish_post` we'd call. ALWAYS, no exceptions. | Canonical owner-gate the sandbox documents and the evaluator scores. The owner taps Approve in Telegram before anything goes live. |
| **`kitchen_reject`** | Any `kitchen_reject_ticket` we'd call — capacity short, lead-time miss, custom-work flag, inventory unsafe. | Owner may want to stretch capacity, partial-fulfil, or call the customer directly. We don't reject silently. |
| **`kitchen_terminal_state`** | Ticket is already `completed`, `rejected`, or `cancelled` and someone re-asked us to act. | Confirm intent — usually a stale event. |
| **`review_low_rating`** | GMB review with `rating ≤ 2`. | Even when the draft is calm and on brand, the owner sees it before it lands. |
| **`review_refund_offer`** | A draft reply contains a refund / replacement / monetary offer. | Owner signs off on money. |

## Owner-gate response shape

```json
{
  "needs_approval": true,
  "summary": "<2-3 sentences for the owner>",
  "draft": "<the exact text or post the owner can approve>",
  "trigger": "ig_post_publish | kitchen_reject | kitchen_terminal_state | review_low_rating | review_refund_offer",
  "channel": "instagram | gmb | kitchen",
  "ref_id": "<scheduledPostId | ticketId | reviewId>"
}
```

The orchestrator's `_extract_json` (see `orchestrator/handlers/`) walks
the first balanced `{...}` block. So:

- The JSON must be the first `{` in the response.
- No prose before it.
- No code fences are required; if you use them, the parser will skip
  past them, but it's cleaner without.

## Things that are NOT triggers

- A 4- or 5-star GMB review → reply directly with `gb_simulate_reply`,
  no gate.
- Accepting a kitchen ticket that fits remaining capacity and isn't
  `requiresCustomWork` → call `kitchen_accept_ticket` directly.
- Marking an already-accepted ticket ready (`kitchen_mark_ready`) →
  no gate; that's a routine state move.
- Scheduling an IG post (`instagram_schedule_post`) → no gate; that's
  the *first half* of the canonical flow. The gate is the publish step.
- A 3-star review with no money on the table → reply directly, but
  acknowledge the gap and offer a clear next step. (4 and 5 stars also
  reply directly.)

## Two-stage IG flow recap

1. **propose stage** (this turn): we read the trigger, draft the
   caption, call `instagram_schedule_post`, and return the owner-gate
   JSON with `trigger="ig_post_publish"` and `ref_id=scheduledPostId`.
   We **do not** call `instagram_publish_post` in this turn.

2. **publish stage** (next turn, after owner approval):
   the orchestrator (or the ig_post smoke harness) has already called
   `instagram_approve_post` for us. We call `instagram_publish_post`
   exactly once, then return a short stdout completion report — no
   JSON wrapper.

The two-call separation is the safety net behind the canonical owner-
gate pattern. `instagram_publish_post` errors hard if approval hasn't
been recorded — that's by design.
