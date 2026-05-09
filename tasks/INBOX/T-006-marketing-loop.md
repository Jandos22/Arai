# T-006: Marketing $500 → $5,000 demand-engine agent

**Owner:** Claude Code (MacBook)
**Branch:** `feat/marketing-agent`
**Estimated:** 90–120 min
**Depends on:** T-001 ✅, T-004 ✅. Independent of T-002/T-003 — can ship without website or orchestrator.

## Why this task first (for CC's track)

The eval has a dedicated scoring function `evaluator_score_marketing_loop`. The launch kit explicitly lists the demand-engine chain we should drive:

```
marketing_create_campaign
  → marketing_launch_simulated_campaign
    → marketing_generate_leads
      → marketing_route_lead
        → marketing_adjust_campaign
          → marketing_report_to_owner
```

This task ships that whole chain, plus the **$500 budget reasoning** the brief calls out as a hard challenge ("$500 must perform like $5,000"). Pure read+plan+write — no webhooks, no Telegram dependency yet.

## Goal

A self-contained Claude Code agent (`agents/marketing/`) that, when invoked via `claude -p` from this folder, plans and executes the full demand-engine chain against the sandbox, producing measurable simulated leads and a written `MARKETING.md` that the evaluator (and Askhat) can read.

## Deliverables

### 1. `agents/marketing/CLAUDE.md`
Per-agent context. Include:
- Role: Marketing Agent for Happy Cake US
- Tools allowed: only `marketing_*`, `square_recent_sales_csv`, `gb_get_metrics`, `marketing_get_margin_by_product`. (Refuse other namespaces — single responsibility.)
- Voice: from `docs/brand/HCU_BRANDBOOK.md` (warm, confident, family-focused, "the original taste of happiness")
- Hard rule: every campaign plan must cite the data it used (sales history, margins, GMB metrics) — no generic marketing advice.
- Audience target: women 25–65 with families, Sugar Land / Houston metro.
- Logging: append every MCP call summary to `evidence/marketing.jsonl` (one JSON line per call: `{ts, tool, args_summary, result_summary, decision_rationale}`).

### 2. `agents/marketing/.mcp.json`
Same `happycake` server block as the root `.mcp.json`. Project-scoped so the marketing agent has its own config without polluting other agents.

### 3. `agents/marketing/run.sh`
One-shot driver script. Executes:
```bash
#!/usr/bin/env bash
set -euo pipefail
set -a; source ../../.env.local; set +a
cd "$(dirname "$0")"
claude -p "$(cat PROMPT.md)"
```

### 4. `agents/marketing/PROMPT.md`
The mission prompt the driver feeds to `claude -p`. Must instruct CC to:
1. Read `marketing_get_budget`, `marketing_get_sales_history`, `marketing_get_margin_by_product`, `square_recent_sales_csv`, `gb_get_metrics(period=last_30_days)`.
2. Compute a budget allocation across instagram / google_local / whatsapp / website / mixed channels using margin × historical conversion. Explain the math.
3. Create 2–3 campaigns with `marketing_create_campaign`. Names must reference brand voice. At least one campaign must target an explicit family/celebration moment (birthday, anniversary).
4. Launch each with `marketing_launch_simulated_campaign`.
5. Generate leads via `marketing_generate_leads` for each campaign.
6. Route every lead with `marketing_route_lead` (decide website vs. WA vs. IG vs. owner_approval per lead context). Record reason.
7. Read metrics with `marketing_get_campaign_metrics`, then `marketing_adjust_campaign` once per campaign (budget shift / audience tweak / offer tweak — your call, justified).
8. Call `marketing_report_to_owner` and capture the response.
9. Write `docs/MARKETING.md` containing: input data summary, budget allocation table, campaign briefs, simulated results, lead routing analysis, adjustments made, owner-report excerpt, and a one-paragraph "if this were real next month" plan.

### 5. `docs/MARKETING.md`
Output of step 9 above. The evaluator will read this; the brief explicitly calls it out as a submission requirement (the $500 case write-up).

### 6. `evidence/marketing.jsonl`
JSONL log of MCP calls. Add `evidence/marketing.jsonl` to `.gitignore` (already covered by `evidence/*.jsonl`) but **commit a sample/redacted snapshot** as `evidence/marketing-sample.jsonl` (last 20 lines, useful for judges to see the shape).

## Acceptance

- [ ] `agents/marketing/run.sh` executes end-to-end and exits 0
- [ ] `evaluator_score_marketing_loop` returns a non-zero / passing score after run (test it: `claude -p "Call evaluator_score_marketing_loop and report"`)
- [ ] `docs/MARKETING.md` exists, references real numbers from the sandbox, no generic advice
- [ ] At least 2 campaigns created, launched, with leads generated, routed, adjusted, reported
- [ ] `evidence/marketing-sample.jsonl` committed (≤ 20 lines, redacted of any token)
- [ ] No token in any committed file (`git diff --cached | grep -i -E '(token|bearer)'` empty)
- [ ] `git diff --stat origin/main` shows only `agents/marketing/`, `docs/MARKETING.md`, `evidence/marketing-sample.jsonl`, `TASKS.md`

## Out of scope

- Telegram bot for `/marketing` command — that's T-003 (orchestrator) work.
- Real Meta/Google Ads APIs — sandbox only.
- Website landing pages — separate task (T-002).
- Multi-month rolling campaigns — single $500/mo plan only.

## Pitfalls

- **The launch kit envelope:** every `tools/call` returns `result.content[0].text` as a JSON-encoded **string**. CC must `json.loads()` (or `JSON.parse`) before treating as an object. Already documented in `docs/MCP-TOOLS.md`. Don't re-discover this the hard way.
- **Idempotency:** if you re-run, you'll create duplicate campaigns. That's OK for the demo, but mention it in MARKETING.md so judges don't assume the count is meaningful.
- **Brand voice:** read `docs/brand/HCU_BRANDBOOK.md` sections 1, 2, 3, 5 before writing any campaign offer text. Specifically: HappyCake is **not** a custom-cake business, **not** trendy, **not** exclusive — they sell ready-made traditional cakes for family moments. Don't write "luxury artisanal" copy.
- **Math transparency:** judges score the marketing **loop**, not the cleverness. A boring, well-justified $200 IG / $200 Google Local / $100 WA reactivation split with cited numbers beats a clever-but-opaque allocation.

## Reporting

Use the T-004 report format plus:
- Branched from: `<commit>`
- `git diff --stat origin/main` output
- Final `evaluator_score_marketing_loop` JSON output
- Any anomaly seen in MCP responses

## After this task

The orchestrator (T-003) will eventually wrap this agent with a Telegram `/marketing` command and overnight scheduling. For now, ship the agent + the doc. We're scoring the loop, not the polish.
