# T-001: Pull team launch kit & populate docs/MCP-TOOLS.md

**Owner:** Claude Code (MacBook — has the login session)
**Branch:** `feat/launch-kit`
**Estimated:** 15 min
**Depends on:** none — start here

## Goal
Get the team's MCP tool catalog out of the launch kit and into the repo so every other task knows what tools exist.

## Why CC, not Hermes
Launch kit is gated behind sign-in. Jandos is signed in on the MacBook, Hermes (Mac mini) is not. Only CC can read it.

## Steps
1. From MacBook browser (already signed in): open https://www.steppebusinessclub.com/hackathon/teams → Jan Solo → **Team launch kit**.
2. Copy the **X-Team-Token** value into `.env.local` (NOT `.env.example`, NOT a commit). Format:
   ```
   STEPPE_MCP_URL=https://www.steppebusinessclub.com/api/mcp
   STEPPE_MCP_TOKEN=<paste here>
   ```
3. Copy everything ELSE from the launch kit page (tool list, sandbox docs, sample requests, any team-specific quickstart) into `docs/MCP-TOOLS.md`.
4. Smoke test the endpoint with the token:
   ```bash
   curl -sS -H "X-Team-Token: $STEPPE_MCP_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
        $STEPPE_MCP_URL | jq .
   ```
   (Adjust if the endpoint expects a different shape — check launch kit docs first.)
5. Append the actual `tools/list` response to `docs/MCP-TOOLS.md` under `## Live tool catalog`.
6. Commit `docs/MCP-TOOLS.md` only. **Verify `git diff --cached` does NOT contain the token.**
7. Push, open PR or merge to `main` if scaffolding hasn't landed yet.

## Acceptance
- [ ] `.env.local` exists on MacBook with valid token (gitignored)
- [ ] `docs/MCP-TOOLS.md` lists every available MCP tool with name + description + input schema
- [ ] Smoke-test curl returns tool list (response captured in doc)
- [ ] No token anywhere in git history (`git log -p | grep -i token` clean)

## Pitfalls
- Some MCP servers want `Authorization: Bearer <token>` instead of `X-Team-Token`. Try both if the first 401s.
- The endpoint may use Streamable HTTP (`text/event-stream`) — if curl hangs, add `-N` and read until first event.
- If endpoint returns HTML, you're not authenticated correctly — re-check header name.
