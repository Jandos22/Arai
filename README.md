# Arai

AI sales + ops system for **Happy Cake US** (Sugar Land, TX).
Built for the **Steppe Business Club Hackathon** — May 9–10, 2026.

**Team:** Jan Solo — Jandos Meirkhan (captain), with Hermes as build-time project-management/documentation helper and Claude Code as the judged agent runtime. Runtime business decisions are made through `claude -p`, not Hermes/Codex/OpenAI.
**Submission deadline:** May 10, 2026, 10:00 CT.

## What this is

A vertical slice that takes a customer from interest → website/WhatsApp/Instagram order intent → POS/cashier → kitchen handoff → owner approval, plus an agent-readable storefront, browser-testable on-site assistant, and a $500/mo marketing plan. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the design and [`CLAUDE.md`](CLAUDE.md) for the team contract.

## Quickstart (fresh clone)

```bash
git clone https://github.com/Jandos22/Arai.git
cd Arai
cp .env.example .env.local
# → fill in STEPPE_MCP_TOKEN (from your team launch kit) and Telegram bot tokens

# website (Next.js storefront + /order + /assistant)
cd website && npm install && npm run dev          # http://localhost:3000
# browser routes: /menu, /order, /assistant
# agent APIs: /agent.json, /api/catalog, /api/policies, /api/order-intent, /api/assistant

# orchestrator (Python spine — scenario loop, dispatcher, evidence)
cd ../orchestrator
uv venv --python 3.12 .venv
uv pip install -r requirements.txt
PYTHONPATH=.. .venv/bin/python -m orchestrator.main --dry-run   # smoke
set -a; source ../.env.local; set +a
PYTHONPATH=.. .venv/bin/python -m orchestrator.main --scenario launch-day-revenue-engine

# (Optional) dedicated per-agent Telegram bots — one chat per role
PYTHONPATH=.. .venv/bin/python -m bots.marketing_bot   # /budget /campaigns /report /run
PYTHONPATH=.. .venv/bin/python -m bots.ops_bot         # /capacity /tickets /reviews
PYTHONPATH=.. .venv/bin/python -m bots.sales_bot       # /menu /threads /orders /pos
```

## Key docs

- [`CLAUDE.md`](CLAUDE.md) — team contract, ownership, hard rules
- [`docs/PLAN.md`](docs/PLAN.md) — strategy, time budget, decision log
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system diagram + event flow + running totals
- [`docs/SUBMISSION.md`](docs/SUBMISSION.md) — brief checklist → repo file mapping
- [`docs/AGENT-NOTES.md`](docs/AGENT-NOTES.md) — agent-friendly website contracts
- [`docs/PRODUCTION-PATH.md`](docs/PRODUCTION-PATH.md) — post-hackathon real-adapter path
- [`docs/EVIDENCE-SCHEMA.md`](docs/EVIDENCE-SCHEMA.md) — JSONL evidence shape
- [`docs/HACKATHON_BRIEF.md`](docs/HACKATHON_BRIEF.md) — original hackathon brief
- [`docs/brand/HCU_BRANDBOOK.md`](docs/brand/HCU_BRANDBOOK.md) — Happy Cake brand book
- [`docs/MCP-TOOLS.md`](docs/MCP-TOOLS.md) — sandbox tool catalog (55 tools)
- [`docs/MCP-SETUP.md`](docs/MCP-SETUP.md) — Claude Code MCP wiring
- [`docs/MARKETING.md`](docs/MARKETING.md) — $500/mo marketing case (T-006, 100/100)
- [`tasks/`](tasks) — task briefs (INBOX → DONE)

## Verification scripts

- [`scripts/test_website.sh`](scripts/test_website.sh) — build + smoke website routes, order-intent API, assistant API, and agent-readable surface (no token needed)
- [`scripts/evaluator_preview.sh`](scripts/evaluator_preview.sh) — call all four `evaluator_score_*` tools + team report against the live sandbox

## Security

**Never commit** `.env.local`, `STEPPE_MCP_TOKEN`, Telegram bot tokens, or any secret. `.gitignore` blocks the obvious. If a token leaks, ping organizers immediately for rotation.
