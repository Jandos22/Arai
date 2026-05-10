# Arai

**Arai is an AI-assisted sales and operations system for small businesses, built for Happy Cake US** (Sugar Land, TX).
Built for the **Steppe Business Club Hackathon** — May 9–10, 2026.

**Team:** Jan Solo — Jandos Meirkhan (captain), with Hermes as build-time project-management/documentation helper and Claude Code as the judged agent runtime. Runtime business decisions are made through `claude -p`, not Hermes/Codex/OpenAI.
**Submission deadline:** May 10, 2026, 10:00 CT.

## What this is

Arai is the system: `orchestrator/` is the Python spine, `agents/` are role-scoped Claude Code projects, and `website/` is the agent-readable storefront plus `/order` and `/assistant` surface. Together they form a vertical slice that takes a customer from interest → website/WhatsApp/Instagram order intent → POS/cashier → kitchen handoff → owner approval, plus a $500/mo marketing loop for a real small business.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the design and [`CLAUDE.md`](CLAUDE.md) for the team contract.

## Quickstart (fresh clone)

```bash
git clone https://github.com/Jandos22/Arai.git
cd Arai

# Secrets: pick one.
# Per-worktree:
cp .env.example .env.local
# Shared across all worktrees:
mkdir -p ~/.config/arai && cp .env.example ~/.config/arai/env.local
# → fill in STEPPE_MCP_TOKEN (from your team launch kit) and Telegram bot tokens

# website (Next.js storefront + /order + /assistant)
cd website && npm install
cd .. && npm run dev                              # http://localhost:3000
# browser routes: /menu, /order, /assistant
# agent APIs: /agent.json, /api/catalog, /api/policies, /api/order-intent, /api/assistant

# orchestrator (Python spine — scenario loop, dispatcher, evidence)
cd ../orchestrator
uv venv --python 3.12 .venv
uv pip install -r requirements.txt
PYTHONPATH=.. .venv/bin/python -m orchestrator.main --dry-run   # smoke
source ../scripts/load_env.sh && arai_load_env ..
PYTHONPATH=.. .venv/bin/python -m orchestrator.main --scenario launch-day-revenue-engine

# (Optional) dedicated per-agent Telegram bots — one chat per role
PYTHONPATH=.. .venv/bin/python -m bots.marketing_bot   # /budget /campaigns /report /run
PYTHONPATH=.. .venv/bin/python -m bots.ops_bot         # /capacity /tickets /reviews
PYTHONPATH=.. .venv/bin/python -m bots.sales_bot       # /menu /threads /orders /pos
```

## Key docs

- [`CLAUDE.md`](CLAUDE.md) — team contract, ownership, hard rules
- [`docs/hackathon/PLAN.md`](docs/hackathon/PLAN.md) — strategy, time budget, decision log
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system diagram + event flow + running totals
- [`docs/SUBMISSION.md`](docs/SUBMISSION.md) — brief checklist → repo file mapping
- [`docs/AGENT-NOTES.md`](docs/AGENT-NOTES.md) — agent-friendly website contracts
- [`docs/PRODUCTION-PATH.md`](docs/PRODUCTION-PATH.md) — post-hackathon real-adapter path
- [`docs/EVIDENCE-SCHEMA.md`](docs/EVIDENCE-SCHEMA.md) — JSONL evidence shape
- [`docs/hackathon/HACKATHON_BRIEF.md`](docs/hackathon/HACKATHON_BRIEF.md) — original hackathon brief
- [`docs/brand/HCU_BRANDBOOK.md`](docs/brand/HCU_BRANDBOOK.md) — Happy Cake brand book
- [`docs/MCP-TOOLS.md`](docs/MCP-TOOLS.md) — sandbox tool catalog (55 tools)
- [`docs/MCP-SETUP.md`](docs/MCP-SETUP.md) — Claude Code MCP wiring
- [`docs/MARKETING.md`](docs/MARKETING.md) — $500/mo marketing case (T-006, 100/100)
- [`tasks/`](tasks) — task briefs (INBOX → DONE)

## Daily reports

A nightly summarizer reads that day's `evidence/orchestrator-*.jsonl` files,
asks `claude -p` for highlights + lowlights + metrics, writes
`evidence/daily-<date>.json`, and (optionally) posts a digest to the owner's
Telegram with an inline "Open audit" button.

Manual run (judges + demo path):

```bash
PYTHONPATH=. orchestrator/.venv/bin/python -m orchestrator.daily_report \
  --date "$(TZ=America/Chicago date +%F)" \
  --post-telegram \
  --audit-url-template "https://<your-tunnel>/audit/{date}"
```

Cron line for production-style usage (host crontab on the runtime machine):

```
0 21 * * *  cd /Users/jandos/dev/Arai && PYTHONPATH=. orchestrator/.venv/bin/python -m orchestrator.daily_report --date "$(TZ=America/Chicago date +\%F)" --post-telegram --audit-url-template "https://<your-tunnel>/audit/{date}" >> ~/.cache/arai-daily.log 2>&1
```

The audit page is served by the orchestrator's existing webhook server
(`orchestrator/webhook_server.py`) over the same Cloudflare tunnel that
ingests inbound webhooks. Two surfaces:

- `GET /audit/<YYYY-MM-DD>` (default) → inline HTML view (highlights,
  lowlights, metrics table, evidence-ref list).
- `GET /audit/<YYYY-MM-DD>` with `Accept: application/json` *or*
  `?format=json` → raw `daily-<date>.json` for agents and judge tooling.
- Missing date → 404 JSON `{"ok": false, "error": "no_daily_report", "date": "<date>"}`.

The "portal" the agents read for follow-up questions is just
`evidence/daily-<date>.json` itself. Bots open it with the shared helper
`orchestrator.daily_report.daily_report_path(date)` rather than recomputing
from raw JSONL.

Tests: `orchestrator/tests/test_daily_report.py` (24 cases) and the audit
endpoint cases in `orchestrator/tests/test_webhook_server.py` (6 cases) —
17-row coverage matrix per `~/.gstack/projects/Jandos22-Arai/jandos-main-eng-review-test-plan-20260510-021302.md`.

## Verification scripts

- [`scripts/test_website.sh`](scripts/test_website.sh) — build + smoke website routes, order-intent API, assistant API, and agent-readable surface (no token needed)
- [`scripts/evaluator_preview.sh`](scripts/evaluator_preview.sh) — call all four `evaluator_score_*` tools + team report against the live sandbox

## Security

**Never commit** `.env.local`, `~/.config/arai/env.local`, `STEPPE_MCP_TOKEN`, Telegram bot tokens, or any secret. `.gitignore` blocks repo-local env files. If a token leaks, ping organizers immediately for rotation.
