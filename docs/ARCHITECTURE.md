# Arai — Architecture

Arai is the whole AI-assisted sales and operations system for Happy Cake US.
The orchestrator is one organ of it: a **scenario-driven Python spine** with
four scoring loops attached. It runs the same `world_next_event` loop the
evaluator drives, so what we test in dev = what's judged.

## High-level diagram

```
                         ┌──────────────────────────────────────┐
                         │  Steppe Sandbox MCP                  │
                         │  (55 tools, 8 namespaces)            │
                         │  https://www.steppebusinessclub.com  │
                         │            /api/mcp                  │
                         └─────────────┬────────────────────────┘
                                       │  X-Team-Token (env)
                                       │  JSON-RPC 2.0 over HTTPS
                                       │
            ┌──────────────────────────┴─────────────────────────────┐
            │                                                        │
   ┌────────▼─────────┐                                  ┌───────────▼──────────┐
   │  orchestrator/   │  shells out via subprocess        │  website/            │
   │  Python spine    │  ─────────────────────────►       │  Next.js storefront  │
   │                  │     claude -p in agents/<role>/   │  /agent.json         │
   │  ┌───────────┐   │                                  │  /api/catalog        │
   │  │ scenario  │   │                                  │  /api/policies       │
   │  │ runner    │   │     ┌─────────────────────────┐   │  /p/[slug] + JSON-LD│
   │  └─────┬─────┘   │     │  agents/sales/           │  └──────────────────────┘
   │        ▼         │     │  agents/marketing/       │
   │  ┌───────────┐   │     │  agents/ops/             │
   │  │ dispatcher│───┼────▶│  (each has CLAUDE.md +   │
   │  └─────┬─────┘   │     │   .mcp.json + run.sh)    │
   │        ▼         │     └─────────────────────────┘
   │  ┌───────────┐   │
   │  │ handlers/ │   │
   │  │  whatsapp │   │
   │  │  instagram│   │
   │  │  gmb      │   │
   │  │  kitchen  │   │
   │  │  marketing│   │
   │  └─────┬─────┘   │
   │        ▼         │     ┌─────────────────────────┐
   │  ┌───────────┐   │     │  Telegram (owner UI)    │
   │  │ telegram_ │───┼────▶│  inline approve/reject  │
   │  │  bot      │   │     │  daily report           │
   │  └───────────┘   │     └─────────────────────────┘
   │                  │
   │  ┌───────────┐   │     ┌─────────────────────────┐
   │  │ evidence  │───┼────▶│  evidence/*.jsonl       │
   │  │  logger   │   │     │  (judge-readable)       │
   │  └───────────┘   │
   └──────────────────┘
```

## Event flow

1. Orchestrator calls `world_start_scenario('launch-day-revenue-engine')`.
2. Loop: `world_next_event` → returns `{channel, type, payload}`.
3. `dispatcher.make_dispatcher` looks up `channel:type` (or `channel:*`,
   then `*`) in the routing table.
4. Handler builds a structured prompt and shells `claude -p` against the
   appropriate `agents/<role>/` Claude Code project. That session has its
   own scoped `.mcp.json` granting access to the `happycake` MCP server.
5. The agent calls MCP tools (catalog read, policy read, send reply, create
   order, create kitchen ticket). Each call is logged to `evidence/*.jsonl`.
6. Owner-gated actions (custom decoration, allergy promise, IG post publish,
   high-value orders) flip into `telegram_bot.request_approval` →
   inline keyboard → on approve, the agent runs the publish-side tool.
7. When the scenario stops emitting events, orchestrator logs
   `world_get_scenario_summary` and exits.

## Routing table (channel:type → handler)

| Channel | Type | Handler | What it does |
|---|---|---|---|
| `whatsapp` | `inbound_message`, `*` | `whatsapp.handle` | Sales agent replies; routes to owner if approval needed |
| `instagram` | `dm`, `comment`, `*` | `instagram.handle` | Sales agent replies; redirects ordering to WA |
| `gmb` | `review_received`, `*` | `gmb.handle` | Ops agent drafts review reply |
| `kitchen` | `ticket_pending_owner_approval`, `*` | `kitchen.handle` | Owner approval gate, then accept/reject ticket |
| `marketing` | `tick`, `*` | `marketing.handle` | Demand-engine chain end-to-end |
| `*` | (unmatched) | drop + log | Visible in evidence so missing routes are obvious |

## Why this shape

| Constraint | How we honor it |
|---|---|
| Claude Code CLI + Opus 4.7 only | All agent reasoning lives in `agents/<role>/`, invoked via `claude -p`; orchestrator is dumb glue, not an LLM framework |
| No SDK / LangGraph / CrewAI / n8n | Orchestrator is plain Python. Routing is a dict. No agent-framework DSL. |
| Owner UI = Telegram only | `telegram_bot` is the only owner channel. No emails, no dashboards. |
| Sandbox is source of truth | `mcp_client` is the only network egress to the sandbox. |
| Evaluator readability | Every decision logged to `evidence/orchestrator-<runId>.jsonl` with redaction. `evaluator_get_evidence_summary` sees the same shape. |

## Entry points

| Command | Purpose |
|---|---|
| `python -m orchestrator.main --dry-run` | Validate wiring, no live calls |
| `python -m orchestrator.main --list-scenarios` | List sandbox scenarios |
| `python -m orchestrator.main --scenario launch-day-revenue-engine` | Live run |

## Files

```
orchestrator/
├── main.py            # CLI entry point
├── mcp_client.py      # JSON-RPC client (X-Team-Token), envelope unwrap
├── scenario.py        # world_start_scenario + world_next_event loop
├── dispatcher.py      # channel:type → handler
├── handlers/          # one module per channel
├── claude_runner.py   # subprocess wrapper for `claude -p`
├── telegram_bot.py    # owner notifier + approval queue
├── evidence.py        # JSONL append, token redaction
├── tests/             # mocked unit tests (no token needed)
├── pyproject.toml
└── requirements.txt
```

## Testing without a token

```bash
cd orchestrator
uv venv --python 3.12 .venv
uv pip install -r requirements.txt
PYTHONPATH=.. .venv/bin/python -m pytest tests
```

24 tests cover `mcp_client`, `dispatcher`, `evidence`, Square capacity
branching, and Claude stream parsing — all deterministic, no token, no
Telegram. The MacBook should also see green when these run there.

## What's actually shipped (running totals)

The four `evaluator_score_*` MCP tools are preview checks, not the whole grade. The official leaderboard uses seven AI judging dimensions (Functional, Depth, Impact, UX, Architecture, Production-readiness, Innovation). See `docs/SELF-EVAL.md` for the current seven-pass risk register.


| Loop | Status | Evidence |
|---|---|---|
| Marketing $500 → $5K | ✅ preview score 100/100 — demand-engine campaigns + routed leads + owner reports | `agents/marketing/`, `docs/MARKETING.md`, `evidence/marketing-sample.jsonl`, `evidence/e2e-sample.jsonl` |
| POS + kitchen | ✅ preview score 100/100 in latest committed sample — POS order + kitchen ticket + explicit `kitchen_get_capacity` / `square_capacity_decision` / ready status | `orchestrator/handlers/square.py`, `evidence/e2e-sample.jsonl`, `docs/SELF-EVAL.md` |
| Channel response (WA / IG / GMB) | ✅ preview score 100/100 — WA/IG/GMB routed through agents; orchestrator now records streamed `agent_tool_use` plus `channel_outbound` rows for outbound proof | `agents/sales/`, `agents/ops/`, `orchestrator/handlers/`, `orchestrator/claude_runner.py` |
| World scenario | ✅ preview score 100/100 — deterministic launch-day scenario runs through `world_start_scenario` / `world_next_event` | `orchestrator/`, `evidence/e2e-sample.jsonl` |
| Owner UI | ✅ Approval queue (T-003) + 3 dedicated bots (`bots/marketing_bot`, `ops_bot`, `sales_bot`) | `orchestrator/telegram_bot.py`, `bots/` |
| Agent-readable site | ✅ `/agent.json`, `/api/catalog`, `/api/policies`, JSON-LD per product (T-002) | `website/`, `docs/AGENT-NOTES.md`, `scripts/test_website.sh` |

## Marketing demand-engine trace (T-006, real run)

The exact MCP call chain a fresh run produces, captured in
`evidence/marketing-sample.jsonl`:

```
marketing_get_budget                        → $500/mo, target $5,000
marketing_get_sales_history                 → 6 months, $14.8K – $19.2K
marketing_get_margin_by_product             → 5 SKUs, 58–68% margin
square_recent_sales_csv                     → cross-checked AOV $25.30
gb_get_metrics(period: last_30_days)        → 1,842 profile views, 87 directions
marketing_create_campaign × 3               → google_local $200, instagram $150, whatsapp $150
marketing_launch_simulated_campaign × 3
marketing_generate_leads × 3                → 9 total leads
marketing_route_lead × 9                    → 5 owner_approval, 2 website, 1 wa, 1 ig
marketing_get_campaign_metrics × 3
marketing_adjust_campaign × 3               → with expectedImpact for each
marketing_report_to_owner                   → final summary
```

This is the chain the brief explicitly asked for, end-to-end, in one
session.
