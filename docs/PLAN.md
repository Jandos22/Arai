# Arai — Plan of attack

> Living document. Source of truth for *what we're building and why*.
> `TASKS.md` is the dashboard for *what's in flight right now*.
> `CLAUDE.md` is the team contract.

Last updated: 2026-05-09, post-T-001 (sandbox catalog known).

---

## Goal in one paragraph

Ship a Claude-Code-CLI-native agentic system that turns Happy Cake US's manual operation into something Askhat would actually use on Monday. Optimize for the four evaluator scoring functions exposed by the sandbox: marketing loop, POS↔kitchen flow, channel response (WA/IG/GMB), and world-scenario execution. Single strong vertical that hits all four, not four mediocre slices.

## Constraints (locked)

- Runtime = Claude Code CLI + Opus 4.7. No SDK, no LangGraph/CrewAI/n8n.
- Owner UI = Telegram only.
- Sandbox MCP at `https://www.steppebusinessclub.com/api/mcp`, `X-Team-Token` header, 55 tools across 8 namespaces.
- 22h calendar budget remaining at plan time. Solo team augmented by Hermes.
- Submission: public Git repo via https://www.steppebusinessclub.com/hackathon/submit before May 10, 10:00 CT.

## Strategy

### What the catalog forced

The eval ships four distinct `evaluator_score_*` functions. A pure single-channel build scores ~25%. We must touch all four loops, but we don't need them equally polished — one excellent + three credible beats four mediocre.

### Spine: scenario-driven orchestrator

A Python orchestrator process drives `world_start_scenario('launch-day-revenue-engine')` → consumes `world_next_event` in a loop → dispatches each event to the right agent. Same loop runs in dev and under the evaluator, so what we test = what's judged.

### Four loops attached to the spine

1. **POS + kitchen** (`evaluator_score_pos_kitchen_flow`)
   `square_create_order` → `kitchen_create_ticket` → owner approval (Telegram) → `kitchen_accept_ticket` / `reject_ticket` → `kitchen_mark_ready` → `square_update_order_status`.

2. **Channels** (`evaluator_score_channel_response`)
   - WA inbound (sim) → sales agent → `whatsapp_send` reply, escalate to order intent if needed.
   - IG DM inbound (sim) → sales agent → `instagram_send_dm`. IG **post** flow uses `instagram_schedule_post` → owner approves in Telegram → `instagram_approve_post` + `instagram_publish_post`. This is the canonical owner-gate pattern, reuse for any judging-visible action.
   - GMB: `gb_list_reviews` → reply via `gb_simulate_reply`; periodic `gb_simulate_post`.

3. **Marketing $500 → $5K** (`evaluator_score_marketing_loop`)
   Full chain: `marketing_get_budget` + `marketing_get_sales_history` + `marketing_get_margin_by_product` → `marketing_create_campaign` → `marketing_launch_simulated_campaign` → `marketing_generate_leads` → `marketing_route_lead` → `marketing_adjust_campaign` → `marketing_report_to_owner`. Budget split decided by margin × conversion math captured in `MARKETING.md`.

4. **World scenario** (`evaluator_score_world_scenario`)
   Above orchestrator IS this loop. We just need to keep the MCP audit log clean and deterministic.

### Owner gate

One pattern, reused everywhere a real-business action would be irreversible: agent calls a `*_schedule` / `*_create` tool → orchestrator pings owner via Telegram with inline Approve/Reject buttons → on approve, agent calls the `_publish` / `_accept` tool. This is what the kit explicitly models for IG; we copy the shape for kitchen tickets, marketing campaign launches, and order intents above $X.

### Visible architecture

Why we're not allowed SDK/n8n: judges want to read the architecture. We help them:
- `ARCHITECTURE.md` with one diagram + an event-flow walkthrough.
- Per-agent `CLAUDE.md` files declaring role, allowed tools, refusal rules.
- `evidence/` JSONL log: every MCP call, every Telegram approval, every agent decision. Judges hit `evaluator_get_evidence_summary` and we want it to look exhaustive.

## Architecture (target)

```
Arai/
├── CLAUDE.md                 ← team contract (root)
├── PLAN.md                   ← this file
├── TASKS.md                  ← live dashboard
├── README.md                 ← fresh-clone bring-up
├── .env.example              ← placeholders only
├── .mcp.json                 ← Happy Cake MCP server, env-interpolated token (T-004)
├── website/                  ← Next.js storefront, agent-readable (T-002, Hermes)
│   ├── app/
│   ├── api/catalog, /policies, /agent.json
│   ├── data/catalog.json     ← snapshotted from square_list_catalog
│   └── scripts/snapshot-catalog.ts
├── orchestrator/             ← Python spine (T-003, Hermes)
│   ├── main.py               ← scenario loop, dispatcher, evidence writer
│   ├── mcp_client.py         ← thin JSON-RPC client w/ X-Team-Token header
│   ├── telegram_bot.py       ← owner UI: approvals, daily report, /marketing
│   └── routes.py             ← event-type → agent mapping
├── agents/                   ← one Claude Code project per role (CC owns)
│   ├── sales/   (CLAUDE.md, .mcp.json, prompt scripts)  ← T-005
│   ├── marketing/                                       ← T-006
│   ├── ops/      (kitchen + GMB)                         ← T-007
│   └── README.md
├── bots/                     ← Telegram bot wrappers (one per agent role)
│   ├── router.py             ← inbound webhook → orchestrator dispatch
│   ├── sales_bot.py
│   ├── marketing_bot.py
│   └── ops_bot.py
├── docs/
│   ├── ARCHITECTURE.md       ← T-009 (Hermes)
│   ├── MCP-TOOLS.md          ← ✅ T-001
│   ├── MCP-SETUP.md          ← T-004
│   ├── MARKETING.md          ← $500 case (T-006)
│   ├── DEMO.md               ← evaluator + human walkthrough (T-009)
│   ├── HACKATHON_BRIEF.md    ← ✅ archived
│   └── brand/HCU_BRANDBOOK.md ← ✅ archived
├── evidence/                 ← JSONL runtime logs (gitignored)
└── tasks/                    ← INBOX → DOING → DONE
```

## Time budget (rough, post-T-001)

| Block | Hours | Owner | What |
|---|---|---|---|
| Now → +2h | 2 | Hermes / CC | T-002 website + T-004 MCP wiring (parallel) |
| +2 → +5h | 3 | Hermes | T-003 orchestrator scaffold + Telegram approval skeleton |
| +5 → +9h | 4 | CC | T-005 sales agent (WA + IG full vertical) |
| +9 → +13h | 4 | CC | T-006 marketing $500 loop end-to-end |
| +13 → +15h | 2 | CC | T-007 GMB review-reply + IG post approval |
| +15 → +17h | 2 | CC | T-008 wire all agents to world-scenario dispatcher |
| +17 → +20h | 3 | Hermes | T-009 ARCHITECTURE.md, DEMO.md, evidence polish, README final |
| +20 → +22h | 2 | Both | T-010 dress rehearsal: fresh clone, evaluator score preview, submit |

(Sleep is in there somewhere. Solo @ venue → CC sessions can run overnight on long tasks; you sleep, I keep writing docs.)

## What we are NOT building

- On-site chat assistant on the website (cool but not in any scoring fn — only do if T-005 ships fast).
- Real Stripe / Square checkout — sandbox only; CTA = WA deeplink.
- Pretty pitch deck. Brief explicitly says judges don't care.
- Multi-agent SDK frameworks. DQ trigger.
- Production deploy of the website (we'll Vercel-deploy at the end if it's free).

## Decision log

- **2026-05-09 11:00 CT** — solo + scenario-spine confirmed after reading kit. Single orchestrator over multi-agent forest because solo can't maintain N independent agents.
- **2026-05-09 11:30 CT** — `.mcp.json` env-interpolated token preferred; `claude mcp add` documented as fallback (T-004 to confirm).
- **2026-05-09 12:00 CT** — TASKS.md adopted at root after CC suggestion; INBOX/DOING/DONE folders kept as detailed-brief storage.

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| `claude -p` rate limits / token burn during long scenario runs | Time-compress with `world_advance_time`; cache static reads (catalog, brandbook) once |
| Webhook setup (Cloudflare Tunnel/ngrok) fails or token-gates | Implement a thin local webhook adapter and prefer Cloudflare Tunnel. Keep `whatsapp_inject_inbound`, `instagram_inject_dm`, and `world_next_event` as fallback/evaluator source of truth, but demonstrate the hard-rule tunnel shape before submission. |
| Solo + tired → bad decisions overnight | CC sessions doing well-scoped tasks while Jandos sleeps; Hermes (Mac mini, no fatigue) writes docs and reviews diffs |
| Token leak in commit | `.gitignore` + per-task acceptance check `git diff --cached \| grep -i token` empty; `.env.local` only |
| Evaluator runs from clone, missing setup step | T-010 dress rehearsal runs `git clone` to a clean dir + brings up everything from `.env.example` only |

## How to override / correct this plan

This file is in the repo. Edit it directly, commit, push. Hermes re-reads on next plan-touch. If urgent: tell Hermes in Telegram "PLAN: <change>" and he'll patch it.
