# T-007: Ops agent — `agents/ops/`

**Owner:** Claude Code (MacBook)
**Branch:** `feat/ops-agent`
**Estimated:** 75–90 min
**Depends on:** T-001 ✅, T-003 ✅, T-004 ✅. Independent of T-005/T-006.

## Why this task

The Ops agent covers two scoring loops the Sales agent doesn't:

1. **GMB review responses** — `evaluator_score_channel_response` checks both
   *existence* and *wording* of replies via `gb_simulate_reply`.
2. **Instagram post approval flow** — the kit calls this out as the canonical
   owner-gate pattern: `instagram_schedule_post` → owner approves in Telegram
   → `instagram_publish_post`. We need to demonstrate it works end-to-end.

It also picks up kitchen state events the Sales agent escalated.

## Deliverables

```
agents/
└── ops/
    ├── CLAUDE.md           # role, tools allowed, refusal rules
    ├── .mcp.json           # happycake server scoped to this project
    ├── PROMPTS/
    │   ├── gmb_review.md
    │   ├── ig_post_proposal.md
    │   └── kitchen_state.md
    ├── policies/
    │   └── escalation_rules.md     # when to call kitchen_reject_ticket etc.
    ├── scripts/
    │   ├── smoke_gmb.sh            # end-to-end review reply test
    │   └── smoke_ig_post.sh        # schedule → owner approve → publish test
    └── README.md
```

## What `agents/ops/CLAUDE.md` must contain

- **Role:** Ops agent for HappyCake US. Handles GMB reviews, Instagram
  scheduled posts (with owner approval gate), and kitchen state transitions
  the Sales agent escalates.
- **Tools allowed:**
  - GMB: `gb_list_reviews`, `gb_simulate_reply`, `gb_simulate_post`,
    `gb_get_metrics`, `gb_list_simulated_actions`
  - Instagram (post side only — DM/comment is Sales): `instagram_schedule_post`,
    `instagram_approve_post`, `instagram_publish_post`,
    `instagram_register_webhook`
  - Kitchen: `kitchen_get_capacity`, `kitchen_get_menu_constraints`,
    `kitchen_list_tickets`, `kitchen_accept_ticket`, `kitchen_reject_ticket`,
    `kitchen_mark_ready`, `kitchen_get_production_summary`
  - **Refuse** Sales-side tools (whatsapp_*, instagram_send_dm,
    instagram_reply_to_comment, square_create_order, marketing_*).
- **Voice:** brandbook §6 (community management) for review replies, §2 for
  general tone. For 1–2 star reviews: open dialogue, never argue, never
  delete, always offer a next step (DM, in-store visit, replacement cake).
- **Owner-gate triggers** (return `{"needs_approval": true, ...}`):
  - Any IG post publish — ALWAYS (this is the canonical gate)
  - Kitchen ticket rejection (capacity / lead time / inventory unsafe)
  - Refund / replacement cake offer in a review reply
  - Any review with rating ≤ 2 — owner sees the draft before it's sent

## Smoke scripts

### `scripts/smoke_gmb.sh`
1. Source `../../.env.local`.
2. List reviews via `gb_list_reviews`; pick the most recent one.
3. Invoke `claude -p` with the GMB-review prompt.
4. Verify `gb_list_simulated_actions` shows a new `reply` entry.
5. PASS / FAIL.

### `scripts/smoke_ig_post.sh`
1. Inject a kitchen-driven content trigger (e.g. "we have honey cake today").
2. Invoke `claude -p` to draft an IG post.
3. Agent calls `instagram_schedule_post` and returns
   `{"needs_approval": true, "scheduledPostId": "...", "draft_caption": "..."}`.
4. Test harness simulates owner approval via `instagram_approve_post`.
5. Agent (called again) sees approval and calls `instagram_publish_post`.
6. PASS / FAIL.

The IG post smoke is the **money shot** — it proves the canonical
owner-gate pattern works end-to-end. Make it visible in evidence.

## Acceptance

- [ ] `agents/ops/CLAUDE.md` written, brandbook-aligned, owner-gate explicit
- [ ] `agents/ops/.mcp.json` valid, env-interpolated
- [ ] `claude mcp list` from `agents/ops/` resolves the `happycake` server
- [ ] `scripts/smoke_gmb.sh` runs, PASS, evidence written
- [ ] `scripts/smoke_ig_post.sh` runs, PASS, three-stage approval evidence
      visible: `instagram_schedule_post` → owner approval (via auto-approve in
      dev or real callback) → `instagram_publish_post`
- [ ] `evidence/ops-sample.jsonl` committed (≤ 30 lines, redacted)
- [ ] Orchestrator dry-run still passes
- [ ] No token in any committed file
- [ ] `git diff --stat origin/main` shows only `agents/ops/`,
      `evidence/ops-sample.jsonl`, `TASKS.md`

## Out of scope

- Sales-side IG DM replies — that's T-005
- Marketing campaigns — that's T-006
- Real Google Business / Meta production access — sandbox only

## Pitfalls

- **GMB reply tone:** brandbook §6 is explicit — don't be defensive, don't
  argue, don't promise things outside our control. Acknowledge → resolve →
  invite back. Even on positive reviews, end with a concrete next thing.
- **IG post approval is two-call:** `instagram_publish_post` will error if
  the post hasn't been approved. Always call `instagram_approve_post` first
  (in production: triggered by Telegram inline keyboard; in smoke: direct
  call to simulate the owner tap).
- **Kitchen rejections:** when capacity says no, return a structured rejection
  reason. Don't just call `kitchen_reject_ticket` and walk away — also
  surface the constraint to the owner via Telegram (orchestrator handles
  that hop if you return `needs_approval: true` first).
- **Don't double-reply** to a review. Check `gb_list_simulated_actions`
  before drafting a reply to confirm we haven't already responded.

## Reporting

Use the T-004 format plus:
- Branched from: `<commit>`
- `git diff --stat origin/main`
- Both smoke outputs (last 30 lines each)
- Notable sandbox quirks
