# T-014: Self-eval agents — 7 shadow-judges + light red-team

**Owner:** Both (CC drives, Hermes assists with templating + docs)
**Branch:** `feat/self-eval`
**Estimated:** 3 hr
**Depends on:** T-008 (need fresh evidence to score). Blocks nothing — bonus track.
**Strategy gate:** only proceed if `bash scripts/evaluator_preview.sh` shows core ≥ 80. Otherwise triage core first per `docs/BONUS-PLAN.md`.

## Why this task

The leaderboard scores 7 dims via 7 AI passes (`docs/HACKATHON-AUDIT.md:24-43`).
The MCP `evaluator_*` tools preview *evidence*, not *grades*. We mirror the
judging pipeline with our own 7 `claude -p` shadow-judges so we can:

1. Find weak dims before submission and fix them.
2. Ship a committed `docs/SELF-EVAL.md` as a visible Innovation +
   Prod-readiness signal — an agentic QA layer that anticipates the rubric.

Hybrid approach: 7 shadow-judges + 2 adversarial scenarios. Full design in
`/Users/jandos/.claude/plans/here-https-www-steppebusinessclub-com-ha-concurrent-galaxy.md`.

## Deliverables

```
agents/
├── eval-functional/{CLAUDE.md,.mcp.json}
├── eval-depth/{CLAUDE.md,.mcp.json}
├── eval-impact/{CLAUDE.md,.mcp.json}
├── eval-ux/{CLAUDE.md,.mcp.json}
├── eval-arch/{CLAUDE.md,.mcp.json}
├── eval-prod/{CLAUDE.md,.mcp.json}
├── eval-inn/{CLAUDE.md,.mcp.json}
└── eval-redteam/
    ├── CLAUDE.md
    ├── scenarios/
    │   ├── allergen-confusion.md
    │   └── last-minute-custom.md
    └── run.sh

scripts/self_eval.sh           # runs 7 in parallel, aggregates
docs/SELF-EVAL.md              # committed first-run output
```

Plus README.md + `docs/ARCHITECTURE.md` updates (one section each).

## Architecture

Pattern mirrors `agents/sales`, `agents/ops`, `agents/marketing`. Each eval
agent gets its own `CLAUDE.md` + `.mcp.json` and runs via the existing
`claude_runner.py:37-49` `claude -p` invocation pattern (cwd=agent dir
auto-loads its `.mcp.json`).

Per-dim input scoping (each agent reads ~10–20% of the repo, not all):

| Dim | Reads (in addition to `evidence/*.jsonl`) | Live MCP |
|-----|------------------------------------------|----------|
| Functional | `agents/*/scripts/*.sh`, `scripts/e2e_smoke.sh`, `orchestrator/handlers/` | `evaluator_score_pos_kitchen_flow`, `evaluator_score_channel_response` |
| Depth | `agents/*/CLAUDE.md`, `agents/*/policies/`, `orchestrator/dispatcher.py` | `evaluator_get_evidence_summary` |
| Impact | `docs/MARKETING.md`, `evidence/marketing*.jsonl` | `evaluator_score_marketing_loop` |
| UX | `website/app/`, `website/public/brand/` | none |
| Arch | `docs/ARCHITECTURE.md`, `orchestrator/main.py`, all `.mcp.json` | none |
| Prod | `.env.example`, `.gitignore`, `scripts/`, `tasks/`, `docs/EVIDENCE-SCHEMA.md` | none |
| Inn | `docs/BONUS-PLAN.md`, `docs/SUBMISSION.md`, README.md, this very pipeline | none |

## What `scripts/self_eval.sh` does

1. Pre-flight: `.env.local` token present, latest `evidence/orchestrator-*.jsonl` < 1hr old.
2. Run all 7 eval agents in parallel via `xargs -P 7` (each
   `cd agents/eval-<dim> && claude -p "..."` with stream-json output).
3. Parse single JSON object from each agent's stdout, validate via `jq`.
4. Compute weighted total (equal weights = 1/7 default).
5. Write `docs/SELF-EVAL.md` (table + top weaknesses + top recommendations)
   and `evidence/self-eval-<timestamp>.json` (raw structured output).
6. Exit 0 if total ≥ 80, else 1.

Mirror `scripts/evaluator_preview.sh:1-80` shape.

## What each eval agent does

- Reads `evidence/*.jsonl` (latest run only) + scoped repo files +
  optional live `evaluator_get_evidence_summary` MCP call.
- Scores its dim 0–100 against a 4–6-criterion rubric.
- Outputs single JSON object:
  ```json
  {
    "dimension": "Functional",
    "score_0_100": 87,
    "rationale": "...",
    "evidence_pointers": [{"path": "...", "what": "..."}],
    "weaknesses": ["..."],
    "recommendations": ["..."]
  }
  ```
- **Hard rule:** every `evidence_pointers[].path` must point to a real
  file. No hallucinated citations. `self_eval.sh` validates via `test -f`.

## Light red-team

Two scripted adversarial scenarios — not a full generator:

1. **Allergen confusion** — customer asks for "nut-free chocolate" then
   later mentions pistachio half-and-half. Tests double owner-gate (allergen + custom).
2. **Last-minute custom** — 3-tier custom cake with 36hr lead time.
   Tests `lead_time_hours` enforcement.

`run.sh` injects each scenario via `whatsapp_inject_inbound` MCP tool,
waits for orchestrator processing, writes the response to
`evidence/redteam-<scenario>-<timestamp>.json`. Subsequent
`self_eval.sh` invocations score that run.

`self_eval.sh --with-redteam` chains both.

## Acceptance

- [ ] `bash scripts/self_eval.sh` exits 0, all 7 dims scored
- [ ] `docs/SELF-EVAL.md` committed with total ≥ 85
- [ ] `--with-redteam` flag injects 2 adversarial scenarios and re-scores
- [ ] All `evidence_pointers[].path` values point to real files
- [ ] No tokens in any committed file
- [ ] README + ARCHITECTURE.md updated with one section each

## Out of scope

- Full red-team scenario generator (just 2 scripted scenarios for v1)
- Tuning weights per dim (equal weights for v1)
- CI integration (pre-push gate is manual for the hackathon)

## Pitfalls

- **Hallucinated citations:** eval agents may cite files that don't exist.
  Mitigation: explicit "must cite real paths" rule in each CLAUDE.md +
  `test -f` check in `self_eval.sh` over every reported path.
- **Rubric too lax:** if all 7 dims score 90+ on first run, the rubric
  isn't honest. Tighten before committing `docs/SELF-EVAL.md`.
- **Scope creep:** if T-008 isn't green or core < 80, abandon this task.
  Bonus is wasted below 80 (per `docs/BONUS-PLAN.md:8-13`).
- **Token cost:** 7 parallel `claude -p` calls = real Opus burn. Each
  agent's prompt should be tight (<2KB) and inputs scoped per dim.
- **Inn agent self-reference:** the Inn agent reads its own existence
  as a signal. Make sure it doesn't double-count — score the *concept*
  of self-eval, not whether the file exists.

## Reporting

Use the T-005/T-007 format plus:
- First-run total + per-dim breakdown table
- 3 weaknesses surfaced + which we fixed in this PR
- Diff `--stat`
- Risky heads-up: any token leak risk, any agent that hallucinated paths

## Coordination

- CC owns: `agents/eval-*/CLAUDE.md` (×8), running `self_eval.sh` (needs
  MCP token in MacBook `.env.local`).
- Hermes owns: README + ARCHITECTURE.md prose updates, `scripts/self_eval.sh`
  shell scaffolding (jq plumbing, timestamp handling), the `eval-redteam`
  scenario markdowns.
- Common files (`docs/SELF-EVAL.md`): whoever runs `self_eval.sh` first
  commits the result. Don't both run it concurrently.
