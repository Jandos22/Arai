# Arai — Task Board

Single source of truth for who's working on what. Update on every commit.

Convention: ID = `T-NNN`. Owner is whoever should *execute* the task. Briefs live in `tasks/INBOX/` (queued), `tasks/DOING/` (in flight), `tasks/DONE/` (shipped).

## In flight

_(none — pick from Queued)_

## Queued

| ID | Title | Owner | Brief |
|----|-------|-------|-------|
| T-008 | End-to-end smoke against a mini scenario — orchestrator + sales + marketing agents working together | CC | `tasks/INBOX/T-008-e2e-smoke.md` |
| T-011 | LocalBusiness JSON-LD + Open Graph + sitemap on website (bonus +5 SEO/Prod) | Hermes | `tasks/INBOX/T-011-localbusiness-seo.md` |
| T-012 | `docs/PRODUCTION-PATH.md` — post-hackathon real-adapter path (bonus +5 Prod) | Hermes | `tasks/INBOX/T-012-production-path.md` |
| T-013 | Sales agent: complaint + custom-cake consultation flows (bonus +5 Real biz pain) | CC | `tasks/INBOX/T-013-sales-bonus-paths.md` |
| T-009 | Final pass: README polish, DEMO.md, evidence sample commit, evaluator preview run | Hermes | TBD |
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

## Architecture intent (locked in by sandbox shape)

Spine = **scenario-driven orchestrator** (Python, shipped in T-003) running `world_next_event` loop. Four scoring loops hang off it:

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
