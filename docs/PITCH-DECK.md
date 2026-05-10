---
marp: true
theme: default
paginate: true
---

# Arai

**AI-assisted sales + ops for HappyCake US**
Steppe Business Club Hackathon — May 10, 2026

Team **Jan Solo** — Jandos Meirkhan
Built with Claude Code (Opus 4.7) + Hermes (build-time PM)

`github.com/Jandos22/Arai`

---

## The shop

- **HappyCake US** — Sugar Land, TX cake & dessert shop
- **$15–20K/month** revenue
- **All manual.** Askhat runs every channel by hand
- **Askhat is the bottleneck**

> Arai takes him out of the bottleneck without taking him out of the decision.

---

## Hard rules (from the brief)

| Rule | Consequence |
|---|---|
| Claude Code CLI + Opus 4.7 only | All reasoning in `agents/<role>/`, invoked via `claude -p` |
| No SDKs, no LangGraph, no n8n | Orchestrator is plain Python. Routing is a `dict`. |
| Owner UI = Telegram only | No emails, no dashboards |
| Sandbox MCP = source of truth | One client, one network egress |
| Webhooks tunnel home | Cloudflare/ngrok → local webhook server |
| Evidence is auditable | Every tool call → `evidence/*.jsonl` |

**These constraints drove the architecture. Lean into them.**

---

## The pitch in 4 beats

1. **The shop** — real bakery, real owner, all manual
2. **The slice** — DM → catalog → order → kitchen → owner approval
3. **The shape** — orchestrator (glue) + 3 scoped agents + Telegram + agent-readable site
4. **The proof** — evidence JSONL + 100/100 marketing trace + 88 tests

---

## Architecture — high level

```
              ┌──────────────────────────────────┐
              │  Steppe Sandbox MCP              │
              │  55 tools, 8 namespaces          │
              │  X-Team-Token, JSON-RPC over HTTPS│
              └─────────────┬────────────────────┘
                            │
        ┌───────────────────┴────────────────────┐
        │                                        │
   ┌────▼─────────┐                    ┌─────────▼────────┐
   │ orchestrator │ ──`claude -p`──►   │ agents/sales     │
   │ Python spine │                    │ agents/ops       │
   │              │                    │ agents/marketing │
   │ scenario     │                    └──────────────────┘
   │ dispatcher   │                    ┌──────────────────┐
   │ handlers     │ ──evidence──►      │ evidence/*.jsonl │
   │ telegram_bot │ ──notify───►       │ Telegram (owner) │
   └──────────────┘                    └──────────────────┘
                            ▲
                            │
                    ┌───────┴──────┐
                    │ website/     │
                    │ /agent.json  │
                    │ /api/catalog │
                    │ /api/policies│
                    │ /assistant   │
                    └──────────────┘
```

---

## The three planes

| Plane | What it does | Doesn't think |
|---|---|---|
| `orchestrator/` | Routes events. Calls `claude -p`. Writes evidence. | ✓ dumb glue |
| `agents/<role>/` | All LLM reasoning. Scoped MCP per agent. | — |
| `website/` | Machine-readable storefront for agents and judges. | ✓ static + JSON |

> "Routing is a dict. That's the whole framework."

---

## Event flow — 7 steps

1. Inbound event → scenario `world_next_event` OR webhook → dispatcher
2. Dispatcher looks up `channel:type` in routing table
3. Handler builds prompt → shells `claude -p` into the right agent
4. Agent calls MCP tools (catalog, capacity, send, create order)
5. Each tool call → `evidence/orchestrator-<runId>.jsonl`
6. Owner-gated action? Agent emits JSON → Telegram card → owner taps
7. Scenario ends → `world_get_scenario_summary` → exit

---

## Routing table

| Channel | Type | Handler |
|---|---|---|
| `whatsapp` | `inbound_message` | sales — reply or owner-gate |
| `instagram` | `dm` / `comment` | sales — reply, redirects to WA |
| `gmb` | `review_received` | ops — drafts reply |
| `kitchen` | `ticket_pending_owner_approval` | ops — owner gate |
| `marketing` | `tick` | marketing — full demand chain |
| `*` | unmatched | drop + log (visible in evidence) |

---

## Three agents — at a glance

| Agent | Owns | MCP tools | Refuses |
|---|---|---:|---|
| **Sales** | WA + IG customer voice | 12 | kitchen state, IG publish, marketing |
| **Ops** | GMB + IG posts + kitchen state | 16 | DMs, order creation, marketing |
| **Marketing** | $500/mo demand engine | 12 | orders, kitchen, customer messaging |

> Capability is enforced at the **MCP scope**, not by polite prompting.

---

## Sales agent — 12 tools

**Read (7):** `square_list_catalog`, `square_get_inventory`, `square_recent_orders`, `kitchen_get_capacity`, `kitchen_get_menu_constraints`, `whatsapp_list_threads`, `instagram_list_dm_threads`

**Write (5):** `whatsapp_send`, `instagram_send_dm`, `instagram_reply_to_comment`, `square_create_order`, `kitchen_create_ticket`

**5 inbound paths:** inquiry / order / owner-gate transactional / **complaint** / **custom-cake consult**

**6 owner-gate triggers:** custom decoration · allergy · > $80 · lead-time · emotional · `requiresCustomWork`

**Order chain:** `square_create_order` → `kitchen_create_ticket` → `whatsapp_send`

---

## Ops agent — 16 tools

**GMB (5):** `list_reviews`, `simulate_reply`, `simulate_post`, `get_metrics`, `list_simulated_actions`

**IG post side (4):** `schedule_post`, `approve_post`, `publish_post`, `register_webhook`

**Kitchen state machine (7):** `get_capacity`, `get_menu_constraints`, `list_tickets`, `accept_ticket`, `reject_ticket`, `mark_ready`, `get_production_summary`

**5 owner-gate triggers:** any IG publish · kitchen reject · refund offers in reviews · ≤ 2★ reviews · GMB post

> **IG publish is two turns, never one.** Schedule → Telegram approval → publish.

---

## Marketing agent — 12 tools

**Demand chain (10):** `get_budget`, `get_sales_history`, `get_margin_by_product`, `create_campaign`, `launch_simulated_campaign`, `generate_leads`, `route_lead`, `get_campaign_metrics`, `adjust_campaign`, `report_to_owner`

**Cross-namespace reads (2):** `square_recent_sales_csv`, `gb_get_metrics`

**Hard rules:** cite the data every time · no invented product facts · math transparency beats cleverness · one adjustment per campaign · refuse spam / dark patterns / fake reviews

---

## Marketing chain — the wow trace

```
get_budget                  → $500/mo, target $5,000
get_sales_history           → 6 months, $14.8K – $19.2K
get_margin_by_product       → 5 SKUs, 58–68% margin
square_recent_sales_csv     → AOV $25.30
gb_get_metrics              → 1,842 views, 87 directions
create_campaign × 3         → $200 / $150 / $150
launch_simulated × 3
generate_leads × 3          → 9 leads
route_lead × 9              → 5 owner / 2 site / 1 wa / 1 ig
get_campaign_metrics × 3
adjust_campaign × 3         → with expectedImpact
report_to_owner             → final summary
```

**Preview score: 100/100. End-to-end in one session.**

---

## Owner-gate JSON contract

When an agent decides "Askhat must approve":
- Stop calling write tools
- Emit a single JSON object
- Orchestrator parses, sends Telegram card with approve/reject

```json
{
  "needs_approval": true,
  "kind": "transactional | complaint | custom_cake_consult",
  "summary": "...",
  "draft_reply": "...",
  "trigger": "over_$80 | allergy | lead_time | emotional | ...",
  "channel": "whatsapp | instagram | gmb | kitchen",
  "to": "<E.164 or threadId or ticketId>"
}
```

> "The agent never executes the side-effect on a gated path. It only **proposes**."

---

## Telegram bots — 4 chats

| Bot | Token env | Commands |
|---|---|---|
| **Arai** (approval gate) | `TELEGRAM_BOT_TOKEN_OWNER` | inline approve/reject |
| **Arai Sales** (read-only) | `TELEGRAM_BOT_TOKEN_SALES` | `/menu /threads /orders /pos` |
| **Arai Ops** (read-only) | `TELEGRAM_BOT_TOKEN_OPS` | `/capacity /tickets /reviews /pending_posts` |
| **Arai Marketing** | `TELEGRAM_BOT_TOKEN_MARKETING` | `/budget /campaigns /report /run` |

- Owner-only — `@owner_only` decorator
- One MCP token, one evidence file across all four
- Auto-approve fallback when owner env vars missing (headless evaluator)

---

## Evidence + daily report

**Live:** every tool call → `evidence/orchestrator-<runId>.jsonl` (token-redacted)

**Daily:** cron 21:00 CT → `daily_report.py`
- reads day's evidence JSONL
- asks `claude -p` for highlights/lowlights/metrics (deterministic Python fallback)
- writes `evidence/daily-<date>.json`
- posts Telegram digest with "Open audit" button

**Audit page:** `GET /audit/<date>` — same Cloudflare tunnel as inbound webhooks

> "The JSON file IS the analytics layer. No SQLite."

---

## We did NOT build the MCP

**Steppe ships the 55-tool sandbox MCP — that's the source of truth (mandated).**

| Namespace | Examples |
|---|---|
| `square_*` | catalog / orders / sales |
| `kitchen_*` | capacity / tickets / state machine |
| `whatsapp_*` | send / threads / inject |
| `instagram_*` | DM / posts / publish |
| `gb_*` | reviews / metrics / simulate |
| `marketing_*` | budget / campaigns / leads |
| `world_*` | scenario harness (orchestrator-only) |
| `evaluator_*` | scoring + team report (judge-only) |

**We authored:** orchestrator, agents (CLAUDE.md + scoped `.mcp.json`), website, Telegram bots, webhook adapter, evidence layer, daily-report pipeline.

---

## 7-pass rubric mapping

| Pass | Weight | Where this architecture earns it |
|---|---:|---|
| Functional scenario tester | 20 | scenario loop, handlers, Square→kitchen, evidence |
| Agent-friendliness auditor | 15 | `/agent.json`, `/api/catalog`, JSON-LD |
| On-site assistant evaluator | 15 | `/assistant`, `/api/assistant`, escalation |
| Code reviewer | 10 | plain Python, 88 tests, scoped agents, redaction |
| Operator simulator | 15 | Telegram gate, capacity checks, 3 role bots |
| Business analyst | 15 | marketing demand engine, production-adapter path |
| Innovation/depth spotter | 10 | machine-readable storefront, scoped MCP, safety paths |

---

## Demo paths

| Path | Wall-clock | Use when |
|---|---|---|
| **A — marketing chain** | ~3 min | **Primary.** `cd agents/marketing && bash run.sh` |
| **B — full scenario** | ~5 min | Watch a longer run; `--scenario launch-day-revenue-engine` |
| **C — webhook tunnel** | ~5 min | Show real-shape inbound; cloudflared + register_webhooks |
| **D — Telegram approval** | ~90 s | After A, dramatic owner-gate moment on phone |
| **Backup — e2e smoke** | ≤ 5 min | If anything stalls. `bash scripts/e2e_smoke.sh` |

---

## What's shipped

| Loop | Status |
|---|---|
| Marketing $500 → $5K | ✅ 100/100 — demand engine + leads + reports |
| POS + kitchen | ✅ 100/100 — capacity-aware accept path |
| Channel response (WA/IG/GMB) | ✅ 100/100 — agent_tool_use + channel_outbound rows |
| World scenario | ✅ 100/100 — deterministic launch-day run |
| Owner UI | ✅ approval queue + 3 role bots |
| Agent-readable site | ✅ `/agent.json`, `/api/catalog`, JSON-LD per product |

---

## Q&A — questions you WILL get

**Why no agent framework?**
Brief banned them. Routing is a 30-line dict. A framework hides architecture from judges and from Askhat.

**How does this become real production?**
`docs/PRODUCTION-PATH.md`. Swap sandbox URL for real adapters (Square, Meta, Google). Agents and handlers don't change.

**What if the LLM hallucinates a price?**
Hard rule: no reply mentions a cake or price unless `square_list_catalog` returned it this session.

**What if Askhat doesn't have his phone?**
Auto-approve fallback is for the evaluator. Production: configurable timeout → backup operator or safe-decline.

**Why three role bots?**
Brief allows one bot per agent. Owner gets a separate chat per concern, no context-switching.

---

## Talking-line cheats

- **"Orchestrator is dumb glue. All reasoning is in the agents."**
- **"Routing is a dict — that's the whole framework."**
- **"Sandbox MCP is the only network egress."**
- **"Every tool call is in `evidence/*.jsonl`."**
- **"Telegram is the owner's whole UI — no dashboards."**
- **"IG post publish is two turns, never one."**
- **"Capability is enforced at the MCP scope, not by polite prompting."**
- **"One MCP token, one evidence file across all four bots."**
- **"`requirements.txt`: httpx, python-telegram-bot, pydantic, pytest. That's it."**
- **"88 tests, no token needed."**

---

## Last-mile checklist (T-30 min)

- [ ] `git pull --rebase` on `main`
- [ ] `echo ${#STEPPE_MCP_TOKEN}` = 41
- [ ] Telegram owner chat has prior message (bots can sendMessage)
- [ ] Website on `:3000` (`cd website && npm run dev`)
- [ ] Webhook server on `:8787` if doing Path C/D
- [ ] `cloudflared tunnel --url http://localhost:8787` if doing C/D
- [ ] `evidence/marketing-sample.jsonl` exists (recorded fallback)
- [ ] Terminal font ≥ 18 pt for the room
- [ ] Phone on silent except Telegram

---

## Closing line

> "The orchestrator is dumb glue.
> The agents are scoped.
> The owner is one tap away.
> Every decision is in the log.
>
> **That's the system. Let me show you it work.**"
