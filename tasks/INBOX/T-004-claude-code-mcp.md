# T-004: Wire the Happy Cake MCP into Claude Code (`.mcp.json`) + smoke test

**Owner:** Claude Code (MacBook — has token)
**Branch:** `feat/cc-mcp`
**Estimated:** 20 min
**Depends on:** T-001 done (catalog known)

## Why
Right now you (CC) can only reach the MCP via curl. To use these 55 tools natively in `claude -p` headless mode (which is the runtime the evaluator clones and runs), the project needs a `.mcp.json` that points Claude Code at the Happy Cake server with `${STEPPE_MCP_TOKEN}`. The launch kit ships the exact snippet — adapt to Claude Code's project config.

## Goal
A `.mcp.json` (or whichever config key Claude Code expects for project-scoped MCP servers) committed to the repo with the **token referenced by env var, not hardcoded**, plus a verified `claude -p` invocation that calls a tool successfully.

## Steps
1. Read https://docs.claude.com/en/docs/claude-code/mcp for the **current** project-scoped MCP config format. (CC, you may know this from your own context — verify against current docs.)
2. Create `.mcp.json` at repo root with the `happycake` server block. Use `${STEPPE_MCP_TOKEN}` interpolation if Claude Code supports it; otherwise document the exact `claude mcp add` command in `docs/MCP-SETUP.md`.
3. Verify the variable interpolation works on a fresh shell — set `STEPPE_MCP_TOKEN` from `.env.local` and run a non-trivial tool from `claude -p`:
   ```
   claude -p "Use the happycake MCP. Call marketing_get_budget. Reply ONLY with the parsed JSON."
   ```
4. Capture the output and commit it as `evidence/T-004-cc-mcp-smoke.txt` (gitignored data dir, but this single file we keep — exempt with `!evidence/T-004-*.txt` in `.gitignore` OR add to `docs/`).
5. Add `docs/MCP-SETUP.md` documenting: how to install, the `${STEPPE_MCP_TOKEN}` requirement, the smoke-test command, and how to add the server to other Claude Code projects (e.g. `agents/sales/`).
6. Update `TASKS.md` (move T-004 to Done with commit hash).

## Acceptance
- [ ] `.mcp.json` at repo root references the token via env, never literal
- [ ] `claude -p "..."` against `marketing_get_budget` returns the budget JSON
- [ ] Smoke output saved to repo (verifiable by judges)
- [ ] `docs/MCP-SETUP.md` lets a fresh-clone CC reproduce the wiring
- [ ] `git diff` clean of any token value

## Pitfalls
- If Claude Code doesn't interpolate env vars in `.mcp.json` natively, fall back to documenting `claude mcp add --transport http happycake $STEPPE_MCP_URL --header "X-Team-Token: $STEPPE_MCP_TOKEN"` and explain that the user runs this once after cloning. Either path is fine; pick whatever the eval can reproduce from a fresh clone with only `.env.local` populated.
- Sub-projects (`agents/sales/.mcp.json` etc.) can have their own scoped configs if useful.

## Out of scope
- Building any agent prompts. T-005 does that.
- Wiring Telegram bots. T-003 does that.
