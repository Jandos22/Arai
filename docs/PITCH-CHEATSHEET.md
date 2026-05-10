# Arai — pitch cheatsheet (phone, single scroll)

> One-page reference. No slide breaks. Scroll-friendly on phone. Bring this on stage.

---

## 30-sec elevator

**HappyCake US** — Sugar Land cake shop, $15–20K/mo, all manual. **Arai** is an AI-assisted sales+ops system: customer DM → catalog → order → kitchen ticket → owner approval, plus a $500/mo marketing loop. Owner UI = Telegram only. Sandbox MCP = source of truth. Every decision in `evidence/*.jsonl`.

## Pitch in 4 beats (≈ 2 min)

1. **The shop.** Real bakery. Askhat is the bottleneck.
2. **The slice.** Customer message → kitchen → owner approval, end-to-end.
3. **The shape.** Orchestrator (dumb glue) + 3 scoped agents + Telegram + agent-readable site.
4. **The proof.** Evidence JSONL + 100/100 marketing chain + 88 tests.

> Closing: *"Orchestrator is dumb glue. Agents are scoped. Owner is one tap away. Every decision is in the log. Let me show you it work."*

## Architecture (one breath)

```
Steppe MCP (55 tools)
       │
       ▼
orchestrator/  ── claude -p ──▶  agents/{sales,ops,marketing}
       │
       ├──▶ Telegram (owner)
       ├──▶ evidence/*.jsonl
       └──▶ website/ (/agent.json /api/catalog /api/policies)
```

## Hard rules → design

- CC CLI + Opus only → reasoning lives in `agents/<role>/`
- No frameworks → routing is a `dict`
- Telegram-only owner UI → no dashboards
- Sandbox = truth → one MCP client, one egress
- Evidence JSONL → token-redacted, judge-readable

## Three agents

| Agent | Tools | Owns | Refuses |
|---|---:|---|---|
| Sales | 12 | WA + IG customer voice | kitchen state, IG publish, marketing |
| Ops | 16 | GMB + IG posts + kitchen state | DMs, order creation, marketing |
| Marketing | 12 | $500/mo demand engine | orders, kitchen, customer messaging |

**Capability enforced at MCP scope, not by prompting.**

## Sales — 5 paths, 6 owner-gate triggers

Paths: inquiry · order · owner-gate transactional · **complaint** · **custom-cake consult**
Triggers: custom decoration · allergy · > $80 · lead-time · emotional · `requiresCustomWork`
Order chain: `square_create_order` → `kitchen_create_ticket` → `whatsapp_send`

## Ops — 5 owner-gate triggers

Any IG publish · kitchen reject · refund offers · ≤ 2★ reviews · GMB posts
**IG publish is two turns, never one.** Schedule → Telegram approve → publish.

## Marketing chain (100/100)

```
get_budget → get_sales_history → get_margin_by_product → square_recent_sales_csv
→ gb_get_metrics → create_campaign ×3 → launch ×3 → generate_leads ×3
→ route_lead ×9 → get_metrics ×3 → adjust ×3 (with expectedImpact)
→ report_to_owner
```

Cite the data every time. Math transparency beats cleverness.

## Owner-gate JSON

```json
{ "needs_approval": true, "kind": "transactional|complaint|custom_cake_consult",
  "summary": "...", "draft_reply": "...", "trigger": "over_$80|allergy|...",
  "channel": "whatsapp|instagram|gmb|kitchen", "to": "..." }
```

Agent stops calling write tools. Orchestrator parses, sends Telegram card.

## 4 Telegram bots

- **Arai** — approval gate (inline approve/reject)
- **Arai Sales** — read-only `/menu /threads /orders /pos`
- **Arai Ops** — read-only `/capacity /tickets /reviews /pending_posts`
- **Arai Marketing** — `/budget /campaigns /report /run`

Owner-only via `@owner_only`. One MCP token, one evidence file across all four.

## We did NOT build the MCP

Steppe ships 55 tools across 8 namespaces (`square_*`, `kitchen_*`, `whatsapp_*`, `instagram_*`, `gb_*`, `marketing_*`, `world_*`, `evaluator_*`). **We consume, scope, and route.** We authored the orchestrator, agents, website, bots, webhook adapter, evidence layer, daily-report pipeline.

## 7-pass rubric

| Pass | W | We earn it via |
|---|---:|---|
| Functional scenario | 20 | scenario loop + handlers + Square→kitchen + JSONL |
| Agent-friendly | 15 | `/agent.json`, `/api/catalog`, JSON-LD |
| On-site assistant | 15 | `/assistant`, `/api/assistant` |
| Code review | 10 | plain Python, 88 tests, scoped agents |
| Operator sim | 15 | Telegram gate, 3 role bots |
| Business analyst | 15 | marketing chain + production-adapter path |
| Innovation | 10 | machine-readable storefront, scoped MCP |

## Demo paths

- **A — marketing** ⭐ primary — `cd agents/marketing && bash run.sh` (~3 min)
- **B — full scenario** — `--scenario launch-day-revenue-engine` (~5 min)
- **C — webhook tunnel** — cloudflared + `register_webhooks.sh` (~5 min)
- **D — Telegram approval** — after A, dramatic phone moment (~90 s)
- **Backup — `bash scripts/e2e_smoke.sh`** if anything stalls

## Q&A — they WILL ask

- **No framework?** Brief banned them. Routing is a 30-line dict.
- **Production?** `docs/PRODUCTION-PATH.md`. Swap MCP URL. Agents don't change.
- **LLM hallucinates a price?** Hard rule: no quote without `square_list_catalog` this session.
- **No phone?** Auto-approve fallback for evaluator. Production: timeout → backup operator.
- **Why 3 role bots?** Brief allows one per agent. Owner gets per-concern chats.

## Talking-line cheats (drop these)

- "Orchestrator is dumb glue."
- "Routing is a dict — that's the whole framework."
- "Capability enforced at MCP scope, not by prompting."
- "IG publish is two turns, never one."
- "Sandbox MCP is the only network egress."
- "One MCP token, one evidence file."
- "88 tests, no token needed."
- "`requirements.txt`: httpx, python-telegram-bot, pydantic, pytest. That's it."

## What's shipped (status)

Marketing $500→$5K · POS+kitchen · WA/IG/GMB response · world scenario · owner UI · agent-readable site — **all ✅, preview 100/100 where scored.**

## T-30 min checklist

- `git pull --rebase` on `main`
- `echo ${#STEPPE_MCP_TOKEN}` = 41
- Telegram owner chat has prior message
- Website on `:3000`
- Webhook server on `:8787` if doing C/D
- `cloudflared tunnel --url http://localhost:8787` if doing C/D
- `evidence/marketing-sample.jsonl` exists (recorded fallback)
- Terminal font ≥ 18 pt
- Phone on silent except Telegram

---

**Closing line:** "Orchestrator is dumb glue. Agents are scoped. Owner is one tap away. Every decision is in the log. **That's the system. Let me show you it work.**"
