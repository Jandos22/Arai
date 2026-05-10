# Arai — Task Board

Single source of truth for who's working on what. Update on every commit.

Convention: ID = `T-NNN`. Owner is whoever should *execute* the task. Briefs live in `tasks/INBOX/` (queued), `tasks/DOING/` (in flight), `tasks/DONE/` (shipped).

## In flight

_(none — pick from Queued)_

## Queued

| ID | Title | Owner | Brief |
|----|-------|-------|-------|
| T-009 | Final pass: README/SUBMISSION polish, final 100/100 evidence sample commit, fresh-clone commands | Hermes | TBD |
| T-010 | Submission dress rehearsal: fresh-clone bring-up, evaluator score preview, push, submit | Both | TBD |

## Done

| ID | Title | Merged | Owner |
|----|-------|--------|-------|
| T-000 | Scaffold: CLAUDE.md, brief, brandbook, .env.example, .gitignore, README | 8ab7873 | Hermes |
| T-001 | Pull launch kit & populate `docs/MCP-TOOLS.md` (55 tools cataloged) | 5d1424c | CC |
| T-004 | `.mcp.json` + claude -p smoke test | da70ae3 | CC |
| T-002 | Website skeleton + agent-readable storefront (Next.js, JSON-LD, /agent.json, /api/catalog, /api/policies, brand palette) | 7144e0e | Hermes |
| T-003 | Orchestrator scaffold (Python spine: MCP client, scenario runner, dispatcher, Telegram, evidence, 15 unit tests) | bc860c4 | Hermes |
| T-006 | Marketing $500 → $5K demand-engine agent (3 campaigns, 9 leads routed, $6,636 projected — `evaluator_score_marketing_loop` 100/100) | aa6a3bf | CC |
| T-005 | Sales agent — `agents/sales/`: WA + IG prompts, owner-gate triggers (custom decoration / allergy / >$80 / lead-time / emotional / requires_custom_work), end-to-end smoke PASS on both paths | c736d14 | CC |
| T-007 | Ops agent — `agents/ops/`: GMB review-reply (rev_001 5★ → cake "Honey" Saturday-bake reply) + canonical IG post owner-gate (schedule → approve → publish, all three stages PASS) + kitchen state prompt + escalation rules | d211d43 | CC |
| T-008 | E2E smoke (`scripts/e2e_smoke.sh`) — committed PASS evidence average 88.75, with final 100/100 local preview pending evidence refresh after capacity-aware handoff | 0de1948 / pending | CC + Hermes |
| T-011 | LocalBusiness JSON-LD + Open Graph + sitemap on website | 7df1674 | Hermes |
| T-012 | `docs/PRODUCTION-PATH.md` — post-hackathon real-adapter path | ca0608d | Hermes |
| T-013 | Sales agent bonus paths — complaint handling + custom-cake consultation, both owner-gated | eeabb4f | CC |
| T-014 | Self-eval agents — seven-pass shadow evaluation + final risk register in `docs/SELF-EVAL.md` | 988497f | CC + Hermes |
| T-015 | Website assistant + source=website order-intent capture (`/assistant`, `/order`, `/api/assistant`, `/api/order-intent`) | this commit | Hermes |

## Architecture intent (locked in by sandbox shape)

Spine = **scenario-driven orchestrator** (Python, shipped in T-003) running `world_next_event` loop. Four preview/scenario loops hang off it (official judges still use seven broader dimensions):

1. **POS + kitchen** — `square_create_order` → `kitchen_create_ticket` chain.
2. **Channels** — WA/IG/GMB inbound → sales agent → outbound; IG posts go through `schedule → owner approval → publish` gate.
3. **Marketing $500** — `marketing_create_campaign` → `launch` → `generate_leads` → `route_lead` → `adjust` → `report_to_owner`.
4. **World scenario** — `world_start_scenario('launch-day-revenue-engine')` drives the evaluator-aligned timeline.

Owner UI = Telegram bot (orchestrator-attached, optional dedicated bots per agent role). Approval pattern = inline keyboard → flips simulator state.

## Coordination rules

- One owner per row in flight
- Branch per work unit, no direct commits to `main`
- `git pull --rebase` before every push
- 15–30 min cadence
- Other-side touches: footer commit message with `@hermes please review` or `@cc please review`
- Skip GitHub PRs; rebase on `origin/main`, fast-forward merge to `main` locally, push `main`
