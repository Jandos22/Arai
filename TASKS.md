# Arai — Task Board

Single source of truth for who's working on what. Update on every commit.

Convention: ID = `T-NNN`. Owner is whoever should *execute* the task. Briefs live in `tasks/INBOX/` (queued), `tasks/DOING/` (in flight), `tasks/DONE/` (shipped).

## In flight

| ID | Title | Owner | Branch | Brief |
|----|-------|-------|--------|-------|
| T-002 | Website skeleton + agent-readable storefront | Hermes | `feat/website` | `tasks/INBOX/T-002-website-skeleton.md` |

## Queued

| ID | Title | Owner | Brief |
|----|-------|-------|-------|
| T-003 | Orchestrator scaffold (Python): MCP client + Telegram bot + scenario loop + evidence logger | Hermes | TBD |
| T-005 | Sales agent: WA/IG inbound → answer → order → kitchen ticket → owner approval | CC | TBD |
| T-006 | Marketing $500 loop agent (full demand-engine chain) + `MARKETING.md` case write-up | CC | TBD |
| T-007 | GMB review-reply + post agent | CC | TBD |
| T-008 | World scenario runner: `world_start_scenario` → consume `world_next_event` → dispatch | CC | TBD |
| T-009 | ARCHITECTURE.md final pass + DEMO.md + evidence schema docs | Hermes | TBD |
| T-010 | Submission dress rehearsal: fresh-clone bring-up, evaluator score preview, push, submit | Both | TBD |

## Done

| ID | Title | Merged | Owner |
|----|-------|--------|-------|
| T-000 | Scaffold: CLAUDE.md, brief, brandbook, .env.example, .gitignore, README | 8ab7873 | Hermes |
| T-001 | Pull launch kit & populate `docs/MCP-TOOLS.md` (55 tools cataloged) | 5d1424c | CC |
| T-004 | Claude Code MCP wiring (`.mcp.json`) + smoke test | 1f47c0e | CC |

## Architecture intent (locked in by sandbox shape)

Spine = **scenario-driven orchestrator** (Python) running `world_next_event` loop. Four scoring loops hang off it:

1. **POS + kitchen** — `square_create_order` → `kitchen_create_ticket` chain.
2. **Channels** — WA/IG/GMB inbound → sales agent → outbound; IG posts go through `schedule → owner approval → publish` gate.
3. **Marketing $500** — `marketing_create_campaign` → `launch` → `generate_leads` → `route_lead` → `adjust` → `report_to_owner`.
4. **World scenario** — `world_start_scenario('launch-day-revenue-engine')` drives the evaluator-aligned timeline.

Owner UI = Telegram bots (one per agent role, +1 router). Approval pattern = inline keyboard → flips simulator state.

## Coordination rules

- One owner per row in flight
- Branch per work unit, no direct commits to `main`
- `git pull --rebase` before every push
- 15–30 min cadence
- Other-side touches: footer commit message with `@hermes please review` or `@cc please review`
