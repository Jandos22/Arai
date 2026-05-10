# Submission checklist — Arai

Arai is an AI-assisted sales and operations system for small businesses,
built for Happy Cake US. The repo name is the product: `orchestrator/` is
the Python spine, `agents/` are role-scoped Claude Code projects, and
`website/` is the storefront/agent surface with website order intake and an
on-site assistant.

This page maps every item the brief asks for to where it lives in the repo,
so judges (and future-us at 9:50 CT) can verify completeness in one pass.

Brief reference: [`docs/HACKATHON_BRIEF.md`](HACKATHON_BRIEF.md) §8 + §12.

## Repo deliverables (brief §8)

| Item | Location | Status |
|---|---|---|
| README with setup from a fresh clone | [`/README.md`](../README.md) | ✅ |
| ARCHITECTURE.md with agents, routing, MCP usage, owner-bot mapping | [`/docs/ARCHITECTURE.md`](ARCHITECTURE.md) | ✅ |
| `.env.example` with placeholders only | [`/.env.example`](../.env.example) | ✅ — verified clean |
| Website / storefront instructions | [`/website/README.md`](../website/README.md), [`/order`](../website/app/order/page.tsx), [`/assistant`](../website/app/assistant/page.tsx) | ✅ |
| Production or local deploy notes | [`/website/README.md`](../website/README.md), [`/orchestrator/README.md`](../orchestrator/README.md) | ✅ |
| Business-impact hypothesis incl. $500 case | [`/docs/MARKETING.md`](MARKETING.md) | ✅ — `evaluator_score_marketing_loop` 100/100 |
| Agent-friendly website notes | [`/docs/AGENT-NOTES.md`](AGENT-NOTES.md) | ✅ |
| On-site assistant test script | [`/scripts/test_website.sh`](../scripts/test_website.sh), [`/api/assistant`](../website/app/api/assistant/route.ts) | ✅ — exercises custom-order escalation and exits 0 on green |
| List of Telegram bots and what each does | [`/bots/README.md`](../bots/README.md) + [`/docs/ARCHITECTURE.md`](ARCHITECTURE.md) | ✅ |
| Post-hackathon real-adapter path | [`/docs/PRODUCTION-PATH.md`](PRODUCTION-PATH.md) | ✅ |
| **Never commit secrets** | `.gitignore` blocks `.env*`, `*.token`, etc. Pre-flight check: `git diff --cached \| grep -iE 'sbc_team\|Bearer'` empty | ✅ |

## Final checklist (brief §12)

| Item | How verified |
|---|---|
| Fresh clone works | `bash scripts/test_website.sh` (no token needed) + `python -m orchestrator.main --dry-run` |
| README setup is clear | Top of [`/README.md`](../README.md) — three commands |
| `.env.example` has placeholders only | `grep -i token .env.example` returns only literal placeholders |
| No secrets in repo | `bash scripts/secret_scan.sh` prints `clean` |
| Website runs | `cd website && npm install && npm run build && npm start` |
| Bot/wrapper runs | `python -m orchestrator.main --dry-run` exits 0 |
| MCP/sandbox calls documented | [`/docs/MCP-TOOLS.md`](MCP-TOOLS.md) — 55 tools + sample curls |
| Demo script exists | [`/docs/DEMO.md`](DEMO.md) — landing in T-008 |
| ARCHITECTURE.md explains the system | [`/docs/ARCHITECTURE.md`](ARCHITECTURE.md) — diagram + event flow + routing table |
| Submission form has correct repo link | https://www.steppebusinessclub.com/hackathon/submit — captain submits with `https://github.com/Jandos22/Arai` |
| Final commit before May 10, 10:00 CT | T-010 dress rehearsal at ~09:00 CT |

## Scoring (brief §9)

**Core = 100 points. Bonus = up to +15. Cap = 115.**

Bonus gating:
- Core 80+ → eligible for up to +15
- Core 60–79 → max +5
- Core <60 → bonus does not apply

See [`BONUS-PLAN.md`](BONUS-PLAN.md) for the bonus-points strategy and ranked targets.

### Core: preview scoring loops + official seven-pass judging

The four `evaluator_score_*` MCP tools are **preview checks** teams can run against the sandbox. They are not the whole leaderboard grade; the official judging uses seven AI dimensions documented in `docs/HACKATHON-AUDIT.md` and summarized in `docs/SELF-EVAL.md`. We still run and cite these preview loops because they expose the concrete sandbox state judges are likely to inspect:

| Loop | What it scores | Where we cover it |
|---|---|---|
| `evaluator_score_marketing_loop` | $500 → $5K demand engine | T-006 — `agents/marketing/` + `docs/MARKETING.md` |
| `evaluator_score_pos_kitchen_flow` | Order intake → kitchen handoff | Website `/api/order-intent` + seeded Square handler + T-005 sales |
| `evaluator_score_channel_response` | WA / IG / GMB reply quality | T-005 (sales side) + T-007 (ops side) |
| `evaluator_score_world_scenario` | Deterministic scenario + audit log | T-003 orchestrator + T-008 e2e smoke |

Combined preview report: `evaluator_generate_team_report({repoUrl})`. Latest committed redacted evidence sample is `evidence/e2e-sample.jsonl` from preview run `20260510T004907Z`: M:100 / POS:100 / Ch:100 / W:100, including `kitchen_get_capacity` + `square_capacity_decision`. Full raw preview JSON files remain local/gitignored unless explicitly inspected for secrets. Official score is expected to combine this evidence with repo/docs/website review across Functional, Depth, Impact, UX, Architecture, Production-readiness, and Innovation.

## Pre-submission ritual

Run from the repo root with `.env.local` populated:

```bash
# 1. Static surface check (no MCP needed)
bash scripts/test_website.sh

# 2. Orchestrator wiring
PYTHONPATH=orchestrator orchestrator/.venv/bin/python -m orchestrator.main --dry-run

# 3. Live evaluator preview
bash scripts/evaluator_preview.sh

# 4. Token leak check
bash scripts/secret_scan.sh

# 5. Final commit + submission
git status         # must be clean
git push origin main
# → submit https://github.com/Jandos22/Arai at https://www.steppebusinessclub.com/hackathon/submit
```

If all five steps print green / non-error, ship it.
