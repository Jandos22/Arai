# DEMO — How to drive Arai end-to-end

A judge or curious operator should be able to read this in 3 minutes and
have the system running in 5. If anything below doesn't work, that's a
bug in this doc — open an issue or just message the team.

---

## 60-second context

**Happy Cake US** is a real Sugar Land cake bakery, ~$15–20K/mo, all
manual. The hackathon brief asks for an AI-assisted sales + ops system
that fixes four channels (website, WhatsApp, Instagram, $500/mo
marketing) and is owner-driven via Telegram only.

**Arai** is the Jan Solo team's AI-assisted sales and operations system
for small businesses, built here for Happy Cake US. In this repo,
`orchestrator/` drives a `world_next_event` loop against the sandbox MCP,
`agents/` holds the per-role Claude Code projects, and `website/` is the
storefront, website order-intent path, and on-site assistant surface. Owner
UI is Telegram. Every decision and tool call is logged to `evidence/*.jsonl`.

See [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) for the diagram.

---

## Setup (≤ 3 min from a fresh clone)

You need: `node ≥20`, `python ≥3.11`, `uv` (or `pip + venv`), `jq`, a
Steppe MCP team token, and (optionally) Telegram bot tokens.

```bash
git clone https://github.com/Jandos22/Arai.git
cd Arai

# Token + (optional) bot tokens
cp .env.example .env.local
$EDITOR .env.local   # paste STEPPE_MCP_TOKEN at minimum

# Python
cd orchestrator
uv venv --python 3.12 .venv
uv pip install -r requirements.txt

# Node
cd ../website
npm install
```

That's it. Nothing else hits the network until you run a tool.

---

## Smoke-test (without burning Claude tokens)

The fastest "does anything work?" check. No LLM calls, no Claude Code
session, no real campaigns. Two commands:

```bash
# 1. Verify the agent-readable website (no MCP needed)
bash scripts/test_website.sh
#   → builds, serves, asserts /agent.json, /api/catalog, /api/policies,
#     JSON-LD on every product page. Exits 0 on PASS.

# 2. Verify the orchestrator wiring (no MCP needed)
PYTHONPATH=orchestrator orchestrator/.venv/bin/python -m orchestrator.main --dry-run
#   → loads CLAUDE.md, builds dispatch table, exits 0, writes one
#     "dry_run" line to evidence/orchestrator-run-<id>.jsonl.

# 3. (Optional) run the orchestrator's mocked tests
PYTHONPATH=orchestrator orchestrator/.venv/bin/python -m pytest orchestrator/tests
#   → 15/15 passing
```

Three green steps = the skeleton is sound. Now hit the live sandbox.

---

## One-command end-to-end smoke (T-008, ≤ 5 min wall-clock)

```bash
bash scripts/e2e_smoke.sh
```

What it does, in order:

1. `orchestrator.main --dry-run` (preflight wiring)
2. Asserts `STEPPE_MCP_TOKEN` is in `.env.local`
3. `tools/list` against the live MCP and asserts ≥ 50 tools
4. Starts the orchestrator on `launch-day-revenue-engine` in the
   background (bounded — `SMOKE_MAX_EVENTS=3`, `SMOKE_ORCH_TIMEOUT=200s`)
5. Injects three sanity events:
   - `whatsapp_inject_inbound` — customer asking for cake "Honey"
   - `instagram_inject_dm` — birthday-cake inquiry
   - `world_inject_event` — 4-star GMB review
6. Waits for the orchestrator (hard-kills at the budget)
7. Calls `evaluator_get_evidence_summary`, all four `evaluator_score_*`,
   and `evaluator_generate_team_report` — prints the four scores
8. On PASS, writes `evidence/e2e-sample.jsonl` (last 50 lines of the
   run, redacted) and exits 0

A green PASS line at the bottom = the system the evaluator runs is the
same loop we run locally.

---

## Live demo path (≤ 5 min, uses Claude Max + sandbox)

### Path A — the marketing engine (T-006, scored 100/100)

The shortest path to a meaningful, judge-visible outcome. The marketing
agent runs the full demand-engine chain end-to-end against the sandbox.

```bash
cd agents/marketing
bash run.sh
# → reads sandbox budget, sales history, margins, GMB metrics
# → creates 3 brand-aligned campaigns ($200/$150/$150)
# → launches each, generates leads, routes them, adjusts, reports
# → ~3-5 min wall-clock, ~50 MCP calls
```

After it exits, look at:

- `docs/MARKETING.md` — the $500 case write-up the brief asks for
- `evidence/marketing-sample.jsonl` — 20 redacted audit lines
- `bash scripts/evaluator_preview.sh` — fetches all 4
  `evaluator_score_*` responses; you'll see `marketing_loop` is 100/100.

### Path B — the orchestrator scenario (free-form)

Drives the same `world_start_scenario('launch-day-revenue-engine')` loop
the evaluator runs, but without the smoke's bounded budget — useful when
you want to watch a longer run.

```bash
set -a; source .env.local; set +a
PYTHONPATH=orchestrator orchestrator/.venv/bin/python \
    -m orchestrator.main \
    --scenario launch-day-revenue-engine \
    --max-events 30
```

While it runs, peek at:

- `evidence/orchestrator-run-<id>.jsonl` (live append)
- Telegram (if `TELEGRAM_BOT_TOKEN_OWNER` + `TELEGRAM_OWNER_CHAT_ID` are
  set) — you'll get notify + approval messages with inline keyboards.

For the bounded, evaluator-aligned version, use `bash
scripts/e2e_smoke.sh` (above).

### Path C — Owner Telegram bots

The brief allows "one bot per agent". Three optional bots, owner-only,
all reuse the orchestrator's MCP client + evidence logger:

```bash
PYTHONPATH=orchestrator orchestrator/.venv/bin/python -m bots.marketing_bot   # /budget /campaigns /report /run
PYTHONPATH=orchestrator orchestrator/.venv/bin/python -m bots.ops_bot         # /capacity /tickets /reviews
PYTHONPATH=orchestrator orchestrator/.venv/bin/python -m bots.sales_bot       # /menu /threads /orders /pos
```

Each runs in its own terminal (use `tmux` if you're efficient about it).
See [`bots/README.md`](../bots/README.md) for the BotFather setup.

---

## What to look for (judges)

| Signal | Where to find it |
|---|---|
| "All four scoring loops touched" | `bash scripts/evaluator_preview.sh` after a marketing + scenario run |
| "Architecture is visible, not a black box" | [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) — diagram + routing table; every module < 200 LOC |
| "Brand voice is honored" | Read any campaign brief in `docs/MARKETING.md`, then `docs/brand/HCU_BRANDBOOK.md` §2 |
| "Owner UI is Telegram only" | Search `git ls-files \| xargs grep -l 'sendMessage\\|inline_keyboard'` — only `orchestrator/telegram_bot.py` + `bots/` show |
| "Sandbox is source of truth" | `git ls-files \| xargs grep -l 'STEPPE_MCP_URL'` — single client at `orchestrator/mcp_client.py` |
| "Evidence is structured" | `head evidence/orchestrator-*.jsonl` after any run; schema in [`docs/EVIDENCE-SCHEMA.md`](EVIDENCE-SCHEMA.md) |
| "No SDK / LangGraph / CrewAI" | `cat orchestrator/requirements.txt` — `httpx`, `python-telegram-bot`, `pydantic`, `pytest`. That's it. |
| "Could be brought to real Happy Cake" | `docs/AGENT-NOTES.md` — explicit deployment story for `/agent.json` + `/api/*` |

---

## Manual exploration (5 things to poke)

If you have an extra 5 minutes, these are the most informative pokes:

1. **Inject a simulated WhatsApp customer** — `claude -p` against
   `agents/sales/` (when T-005 lands) with
   `whatsapp_inject_inbound(from="+12815550000", message="Do you have
   honey cake today for tomorrow?")` and watch the agent reply.
2. **Read a product agent-side** — `curl
   https://localhost:3000/p/medovik-honey-cake | grep -A 30
   application/ld+json` — full schema.org Product on every page.
3. **Look at a campaign adjustment** — `jq 'select(.tool ==
   "marketing_adjust_campaign")' evidence/marketing-sample.jsonl` — every
   adjustment cites an `expectedImpact`.
4. **Watch the world timeline** — `claude -p "Call world_get_timeline and
   summarize"` from the repo root.
5. **Run `evaluator_generate_team_report`** — it's the same call the
   leaderboard uses; included in `scripts/evaluator_preview.sh` output.

---

## Caveats and known shapes

- **Idempotency:** every smoke run creates a new orchestrator evidence
  file (`evidence/orchestrator-run-<id>.jsonl`). The evaluator scores on
  the team's cumulative sandbox audit log — re-running the smoke does
  not "reset" prior scores, just adds more activity.
- **Bounded budget vs raw score:** the smoke caps the orchestrator at
  ~3 events / 200s so it stays under the 5-min budget. With per-event
  `claude -p` calls running 30–90s, not every injected event finishes
  end-to-end. The latest committed evidence sample shows all four preview
  scores at 100/100, including the capacity-aware POS/kitchen path. If a
  future bounded run returns lower, check whether the cumulative audit log
  already contains the complete path before treating it as a regression.
- **No real WA/IG/POS:** every inbound and outbound message lives in the
  sandbox — `*_inject_*` test tools are the entry point.

---

## Going further

- [`docs/SUBMISSION.md`](SUBMISSION.md) — checklist mapping every brief
  requirement to a file.
- [`docs/AGENT-NOTES.md`](AGENT-NOTES.md) — the agent-friendly website
  contract design.
- [`docs/PLAN.md`](PLAN.md) — the actual plan we worked from, with
  decision log and risk register.
- [`tasks/`](../tasks) — every task brief Hermes (build-time PM/helper, not the judged runtime) wrote
  for Claude Code, in the exact format CC executed.
