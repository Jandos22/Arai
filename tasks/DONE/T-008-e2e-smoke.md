# T-008: End-to-end smoke against a mini scenario

**Owner:** Claude Code (MacBook)
**Branch:** `feat/e2e-smoke`
**Estimated:** 60–75 min
**Depends on:** T-005 ✅, T-006 ✅, T-007 ✅, T-003 ✅. Blocks T-009/T-010.

## Why this task

Before submission we need **one command** that:

1. Stands up the orchestrator
2. Drives a sandbox scenario for a bounded number of events
3. Triggers all four `evaluator_score_*` scoring loops
4. Writes a clean evidence trail
5. Calls `evaluator_get_evidence_summary` and prints the team report

If this command exits 0 with non-zero scores across all four loops, we're
ship-ready. The evaluator runs essentially the same loop, so a green local
run means a green eval.

## Deliverables

```
scripts/
└── e2e_smoke.sh           # the one command (repo root)
docs/
└── DEMO.md                # walkthrough an evaluator can follow by hand
evidence/
└── e2e-sample.jsonl       # last 50 lines of a successful run, redacted
```

## What `scripts/e2e_smoke.sh` should do

1. Print preflight: `python -m orchestrator.main --dry-run` → must exit 0.
2. Verify `.env.local` has `STEPPE_MCP_TOKEN`. If not, fail fast.
3. Print the live tool list: `claude -p "List MCP tools as JSON"` and assert
   the count is ≥ 50 (sanity check the MCP wiring).
4. Start the orchestrator with a **bounded** scenario:
   - `--scenario launch-day-revenue-engine`
   - `--max-events 30`
   - Run for at most 4 minutes wall-clock (kill if it stalls).
5. While it runs, in parallel inject a few sanity events to guarantee
   coverage of all four scoring loops:
   - `whatsapp_inject_inbound` — a customer asking about Medovik
   - `instagram_inject_dm` — a customer asking about birthday cake date
   - `world_inject_event` (gmb / review_received) — a 4-star review
   - Trigger marketing via dispatch — `marketing:tick`
6. After the scenario settles, call:
   - `evaluator_get_evidence_summary`
   - `evaluator_score_marketing_loop`
   - `evaluator_score_pos_kitchen_flow`
   - `evaluator_score_channel_response`
   - `evaluator_score_world_scenario`
   - `evaluator_generate_team_report` with `repoUrl=https://github.com/Jandos22/Arai`
7. Print a single PASS/FAIL line based on:
   - Dry-run + tool-list passed
   - All four score calls returned non-error responses
   - At least one MCP write call per scoring loop visible in evidence
8. Save the last 50 lines of `evidence/orchestrator-run-*.jsonl` (redacted)
   to `evidence/e2e-sample.jsonl` and commit it.

## What `docs/DEMO.md` must contain

A judge can read this in 3 minutes and run the system in 5:

1. **One paragraph** of context (Happy Cake US, what Arai does).
2. **Setup** (3 commands: clone, fill `.env.local`, install).
3. **Run** (one command: `bash scripts/e2e_smoke.sh`).
4. **What to look for**:
   - Where the evidence file lands
   - Which Telegram messages they'll see if `TELEGRAM_BOT_TOKEN_OWNER` is set
   - Which evaluator tools we call and what scores indicate
5. **Manual exploration** — 5 things a judge can do to poke at the system
   beyond the smoke (call `world_get_timeline`, inspect the website,
   trigger a custom WA inject, etc.).
6. **Architecture link** — pointer to `docs/ARCHITECTURE.md` for depth.

## Acceptance

- [ ] `scripts/e2e_smoke.sh` runs from a fresh clone (after `.env.local`
      and installs) and exits 0
- [ ] All four `evaluator_score_*` calls return non-error responses
- [ ] `evidence/e2e-sample.jsonl` committed, ≤ 50 lines, redacted
- [ ] `docs/DEMO.md` reads cleanly to a non-author
- [ ] No token in any committed file
- [ ] Smoke total runtime ≤ 5 minutes wall-clock
- [ ] `python -m orchestrator.main --dry-run` still passes after this lands

## Out of scope

- Real ngrok inbound — smoke uses sandbox `*_inject_*` test tools
- Tuning agent prompts beyond bug fixes — that's T-009 polish

## Pitfalls

- **Idempotency:** running smoke twice creates duplicate orders and
  campaigns. Either reset via `world_start_scenario` (which resets timeline)
  or note this clearly in DEMO.md so judges don't penalize duplicate counts.
- **`--max-events` matters:** without it, scenarios can run for the full
  480 sim-min and burn Claude tokens. Bounded run is non-negotiable.
- **Score interpretation:** the `evaluator_score_*` tools return JSON; the
  *raw score* is less important than *non-error response with evidence*.
  Don't fail the smoke just because a score is low — the eval pipeline does
  its own scoring later.
- **Evidence redaction:** before committing `evidence/e2e-sample.jsonl`,
  spot-check it for any leaked token. The orchestrator redacts on write,
  but defense-in-depth: `grep -i 'sbc_team\|bearer'` should be empty.

## Reporting

Use the T-004 format plus:
- Smoke output last 60 lines (with PASS line)
- All four `evaluator_score_*` JSON responses
- Final `evaluator_generate_team_report` excerpt (top of the JSON)
