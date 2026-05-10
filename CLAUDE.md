# CLAUDE.md — Project Arai

> Auto-loaded by Claude Code. Read this first, every session.

## Project

**Arai** — Steppe Business Club Hackathon submission.
**Client:** Happy Cake US (Sugar Land, TX) — local cake & dessert shop, ~$15–20K/mo, all-manual ops.
**Goal:** AI-assisted sales + ops system. One strong vertical slice from customer interest → order intent → kitchen handoff → owner approval, with an agent-readable storefront and a $500/mo marketing plan.
**Deadline:** May 10, 2026, 10:00 CT.
**Repo:** https://github.com/Jandos22/Arai (must be public at submission).
**Submission form:** https://www.steppebusinessclub.com/hackathon/submit

## Team — "Jan Solo"

This is a solo team **augmented by two AI collaborators**. Treat it as a 3-member team.

| Member | Role | Where it runs |
|---|---|---|
| **Jandos Meirkhan** | Captain, operator, decision-maker, demo lead | MacBook (at venue) |
| **Hermes** | Project manager, scaffolding, docs, website, marketing math, repo hygiene | Mac mini (home), reachable via Telegram |
| **Claude Code (you)** | Agent runtime — the system being judged. Builds and runs the live agents against the sandbox MCP. | MacBook |

**Hermes is a build-time collaborator, not the judged runtime.** Hermes drives planning/docs/scaffolding in parallel and pushes normal git commits. The judged business-agent runtime remains Claude Code CLI via `claude -p` plus this Python orchestrator. You (Claude Code) and Hermes share this repo; coordinate via branches and commit messages — never both edit the same file at once.

## Hard rules (DQ if violated)

- Runtime = **Claude Code CLI + Opus 4.7** only. No Claude Agent SDK. No LangGraph, CrewAI, n8n.
- Owner UI = **Telegram bots only**. No email, no web dashboard for the owner.
- Pattern: WhatsApp/Instagram webhook → ngrok/Cloudflare Tunnel → bot wrapper → `claude -p "<prompt>"` headless → response back to channel.
- Sandbox MCP is the source of truth. No real Square/WA/IG/payment credentials.
- **NEVER commit `STEPPE_MCP_TOKEN`** or any secret. Load secrets through `scripts/load_env.sh`; shared worktree env lives at `~/.config/arai/env.local`, with repo-local `.env.local` only as an override/fallback. `.env.example` ships placeholders.

## Architecture intent (subject to evolution; keep ARCHITECTURE.md authoritative)

Vertical slice we are building:

1. Customer DMs Instagram OR messages WhatsApp.
2. Webhook → bot wrapper (Python) → `claude -p` with project context.
3. Agent uses MCP tools (catalog, inventory, policies, kitchen, orders) to answer in Happy Cake brand voice.
4. Order intent captured → kitchen handoff card created in sandbox.
5. Owner gets Telegram message with inline approve/reject buttons for custom or high-value orders.
6. All decisions + tool calls logged to `evidence/` (SQLite + JSONL) so the 7-pass evaluator can verify.

Sub-systems:
- `website/` — Next.js storefront `happycake.us` with agent-readable JSON-LD catalog and `/api/catalog`, `/api/policies`, `/agent.json`. (T-002 ✅)
- `orchestrator/` — Python spine: MCP client, scenario runner (`world_next_event` loop), event dispatcher, `claude -p` per-agent shell-out, Telegram owner notifier with approval queue, evidence JSONL writer. (T-003 ✅)
- `agents/` — one Claude Code project per role (sales, ops, marketing). Each has its own `CLAUDE.md` and scoped `.mcp.json`. The orchestrator picks them up automatically when their dirs exist.
- `evidence/` — runtime logs (gitignored except sample/schema docs).
- `docs/` — README, ARCHITECTURE.md, EVIDENCE-SCHEMA.md, MARKETING.md, DEMO.md.

## MCP

- Endpoint: `https://www.steppebusinessclub.com/api/mcp`
- Auth: `X-Team-Token` header, value from `STEPPE_MCP_TOKEN`.
- Before any live MCP smoke/test, prefer shared env loading:
  ```bash
  source scripts/load_env.sh && arai_load_env "$PWD"
  echo ${#STEPPE_MCP_TOKEN}  # expected: 41; never echo the token value
  ```
- `arai_load_env` checks `ARAI_ENV_FILE`, then repo `.env.local`, then `~/.config/arai/env.local`.
- Tools available: see `docs/MCP-TOOLS.md` (Hermes will populate from launch-kit info).

## Coordination protocol

- **Branches:** `feat/<area>` (e.g. `feat/website`, `feat/sales-agent`, `feat/bots`). No direct commits to `main`.
- **Sync:** `git pull --rebase` before every push.
- **Cadence:** small commits, push every 15–30 min so the other side can pull.
- **Ownership defaults:** Hermes owns `website/`, `docs/`, `bots/router.py`, `.env.example`, `.gitignore`. Claude Code owns `agents/*/`, `bots/*-bot.py` (per-agent runtime), MCP wiring code that needs the live token.
- **If you need to touch Hermes-owned files:** leave a comment in the commit message `@hermes please review`.

## Judging signals (optimize for these)

1. Architecture is **visible and explainable** — not a black box (this is exactly why SDK/n8n are banned).
2. Evidence in logs/state — every agent decision and tool call recorded.
3. Vertical slice end-to-end working > 4 broad half-finished channels.
4. Owner-realism — Askhat himself should want to use it.
5. Scalability — system can be brought close to real Happy Cake deployment.
6. README + ARCHITECTURE.md let a fresh clone come up cleanly.

## Don't

- Don't invent product facts. If catalog/policy isn't in MCP or brandbook, ask, don't fabricate.
- Don't expose any owner UI outside Telegram.
- Don't commit secrets — pre-commit hook will block, but stay vigilant.
- Don't expand scope. Narrow + working > broad + half-done.

## Status

Updated by whichever team member touches the repo. Last updated: scaffold-time.
