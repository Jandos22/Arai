# T-003: Orchestrator scaffold — Python spine

**Owner:** Hermes (Mac mini)
**Branch:** `feat/orchestrator`
**Estimated:** 120 min
**Depends on:** T-001 ✅ (catalog known), T-004 ✅ (MCP wiring confirmed)

## Why

The launch-kit ships a `world_start_scenario` / `world_next_event` loop that the
**evaluator itself runs** to test our system. To score across all four
`evaluator_score_*` functions, we need a Python process that:

1. Drives that scenario loop in dev (so we test exactly what the eval tests)
2. Routes each event to the right agent (sales, ops, marketing)
3. Uses Telegram as the owner UI for approvals / daily report
4. Writes JSONL evidence judges can read via `evaluator_get_evidence_summary`

This is the **spine**. Agents (T-005, T-006, T-007) attach to it.

## Goal

A working `orchestrator/` package that:

- Connects to the sandbox MCP via `X-Team-Token` (read from `.env.local`)
- Starts and consumes the `launch-day-revenue-engine` scenario
- Dispatches events to handlers (one per channel/type)
- Calls `claude -p` for any handler that needs LLM reasoning, with the
  appropriate per-agent project (`agents/sales/`, `agents/marketing/`, etc.)
- Sends owner messages and approval prompts via Telegram
- Logs every MCP call + every decision to `evidence/orchestrator.jsonl`
- Exits cleanly with a final scenario summary

## Deliverables

```
orchestrator/
├── __init__.py
├── mcp_client.py       # JSON-RPC over HTTPS, X-Team-Token, retries, parse content[0].text
├── evidence.py         # JSONL append, redaction, schema doc
├── telegram_bot.py     # owner UI: approve/reject inline keyboards, daily report, /marketing
├── scenario.py         # world_start_scenario + world_next_event loop driver
├── dispatcher.py       # event-type → handler mapping
├── handlers/
│   ├── __init__.py
│   ├── whatsapp.py     # forwards to claude -p in agents/sales/
│   ├── instagram.py    # forwards to claude -p in agents/sales/
│   ├── gmb.py          # forwards to claude -p in agents/ops/
│   ├── kitchen.py      # owner approval gate for tickets
│   └── marketing.py    # forwards to claude -p in agents/marketing/
├── claude_runner.py    # subprocess wrapper for `claude -p`, evidence-logged
├── main.py             # entry point: orchestrator run [--scenario ID] [--dry-run]
├── tests/
│   ├── test_mcp_client.py     # mocks responses; verifies envelope unwrap
│   ├── test_dispatcher.py     # routing rules
│   └── test_evidence.py       # redaction + schema
├── pyproject.toml      # uv-managed; targets py3.11+
├── requirements.txt    # pip fallback for fresh-clone bring-up
└── README.md
docs/
├── ARCHITECTURE.md     # diagram + event flow
└── EVIDENCE-SCHEMA.md  # JSONL line shape
```

## Acceptance

- [ ] `cd orchestrator && uv run python -m orchestrator.main --dry-run` exits 0
- [ ] Live mode (with `STEPPE_MCP_TOKEN`) starts a scenario, processes ≥3 events, writes evidence
- [ ] All MCP calls go through `mcp_client.call_tool()` — no ad-hoc `requests.post` elsewhere
- [ ] Evidence JSONL line schema documented in `docs/EVIDENCE-SCHEMA.md`
- [ ] No token in any committed file
- [ ] `pytest orchestrator/tests` passes (mocked, no live token needed)
- [ ] `docs/ARCHITECTURE.md` exists with one diagram + event-flow table

## Out of scope

- Agent prompt content for sales/ops/marketing (that's T-005/T-006/T-007)
- Real ngrok/CF Tunnel inbound — sandbox `*_inject_*` test tools are enough for dev + eval

## Notes / pitfalls

- MCP envelope: `result.content[0].text` is a JSON-encoded **string** — `json.loads()` it
- Auth: `X-Team-Token` (NOT `Authorization: Bearer`) — verified in T-004
- `claude -p` is fire-and-forget per call; capture stdout, don't try to stream
- Telegram inline keyboards: use python-telegram-bot v21 callback_query pattern

---

## Outcome (2026-05-09, Hermes)

Shipped. `orchestrator/` package live with:

- `mcp_client.py` — JSON-RPC client, `X-Team-Token` auth, envelope unwrap
- `evidence.py` — JSONL append + token redaction, schema in `docs/EVIDENCE-SCHEMA.md`
- `scenario.py` — `world_start_scenario` + `world_next_event` loop with backoff
- `dispatcher.py` — `channel:type` → handler with `*` wildcard fallback
- `handlers/{whatsapp,instagram,gmb,kitchen,marketing}.py` — thin prompt builders
- `claude_runner.py` — subprocess wrapper for `claude -p` per agent project
- `telegram_bot.py` — owner notifier + approval queue (auto-approves in dev when no token)
- `main.py` — CLI: `--dry-run`, `--list-scenarios`, `--scenario <id>`
- `tests/` — 15 unit tests, mocked via `respx`, no token needed

Verified:
- `pytest tests` → 15 passed in 0.04s
- `python -m orchestrator.main --dry-run` → exits 0, writes evidence file
- All MCP egress goes through `mcp_client.MCPClient.call_tool` (single chokepoint)

Docs:
- `docs/ARCHITECTURE.md` — diagram + event flow + routing table
- `docs/EVIDENCE-SCHEMA.md` — JSONL line shape per `kind`
- `orchestrator/README.md` — quickstart + tests + live-run

Ready for agent attachment (T-005, T-006, T-007). When `agents/<role>/` dirs
exist, the orchestrator picks them up automatically; otherwise it logs a
`channel_dropped` row so missing agents are visible.
