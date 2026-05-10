# MCP setup — Happy Cake sandbox

How to make the 55-tool Happy Cake MCP server reachable from `claude -p` in
this repo. This is the runtime the evaluator will reproduce: clone the repo,
populate one env var, and `claude -p` can call sandbox tools natively.

Owner: any team member after fresh clone.
Verified by: `evidence/T-004-cc-mcp-smoke.txt`.

## How the wiring works

`.mcp.json` at the repo root declares one project-scoped MCP server:

```json
{
  "mcpServers": {
    "happycake": {
      "type": "http",
      "url": "${STEPPE_MCP_URL}",
      "headers": {
        "X-Team-Token": "${STEPPE_MCP_TOKEN}"
      }
    }
  }
}
```

- `${VAR}` interpolation is a Claude Code feature — values are pulled from
  the shell environment when the session starts.
- Zero literal credentials in the file. The token never enters git.
- Tools surface inside Claude Code as `mcp__happycake__<toolname>` (e.g.
  `mcp__happycake__marketing_get_budget`).

## One-time setup on a fresh clone or worktree

1. For one worktree, copy `.env.example` to `.env.local`:
   ```bash
   cp .env.example .env.local
   ```
   For all worktrees on the same machine, prefer one shared file:
   ```bash
   mkdir -p ~/.config/arai
   cp .env.example ~/.config/arai/env.local
   ```
2. Paste the team token (from `STEPPE_MCP_TOKEN` in the launch kit) into the
   env file. Leave `STEPPE_MCP_URL` at its default.
3. Verify repo-local `.env.local` is gitignored — `git status` should not list it.

## Running `claude -p` with the MCP

Claude Code does **not** auto-load env files. Export the vars into the shell
before invoking `claude`:

```bash
cd /path/to/Arai
source scripts/load_env.sh && arai_load_env "$PWD"
claude -p "Use happycake MCP. List available tools."
```

Env lookup order is `ARAI_ENV_FILE`, repo `.env.local`, then
`~/.config/arai/env.local`. Never echo token values; use
`echo ${#STEPPE_MCP_TOKEN}` to check presence by length only.

For non-interactive runs (the bot wrappers, evaluators), pre-allow the
specific tools you intend to call so no permission prompt blocks the run:

```bash
echo "Call marketing_get_budget. Reply with ONLY the JSON." \
  | claude -p \
      --permission-mode bypassPermissions \
      --allowedTools "mcp__happycake__marketing_get_budget"
```

Use the narrowest `--allowedTools` list that the agent actually needs.
`bypassPermissions` skips the trust dialog; the `--allowedTools` whitelist
is what actually constrains the surface.

## Smoke test

```bash
cd /path/to/Arai
source scripts/load_env.sh && arai_load_env "$PWD"
echo "Use the happycake MCP server. Call the marketing_get_budget tool with no arguments. Reply with ONLY the parsed JSON result — no prose, no code fences." \
  | claude -p \
      --permission-mode bypassPermissions \
      --allowedTools "mcp__happycake__marketing_get_budget"
```

Expected (current sandbox):

```json
{
  "monthlyBudgetUsd": 500,
  "targetEffectUsd": 5000,
  "challenge": "$500 -> $5,000"
}
```

If you get this back, the wiring is good. Captured baseline:
`evidence/T-004-cc-mcp-smoke.txt`.

## Adding the MCP to a sub-project (e.g. `agents/sales/`)

When we scaffold per-agent Claude Code projects under `agents/`, each can
either:

- Reuse this root `.mcp.json` by running `claude -p` from the repo root with
  `--add-dir agents/sales`, OR
- Have its own `agents/sales/.mcp.json` mirroring the same block.

Prefer option 1 unless an agent needs to *exclude* tools the others use.

## Troubleshooting

- **`Unauthorized` / 401** — `STEPPE_MCP_TOKEN` not in shell env. Re-run
  `source scripts/load_env.sh && arai_load_env "$PWD"` and confirm with
  `echo ${#STEPPE_MCP_TOKEN}` (length only — never echo the value).
- **No `mcp__happycake__*` tools listed** — Claude Code didn't load
  `.mcp.json`. Make sure you launched `claude` from the repo root (or pass
  `--add-dir` / `--mcp-config .mcp.json`).
- **Workspace trust dialog blocks `-p`** — pass
  `--permission-mode bypassPermissions` for headless runs.
- **Token rotated mid-session** — restart the `claude` session; env-var
  interpolation happens at server-spawn time, not per-call.
