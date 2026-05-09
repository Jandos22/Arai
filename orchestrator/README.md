# orchestrator/

Python spine for the Arai system. Drives the sandbox `world_start_scenario` /
`world_next_event` loop, dispatches each event to a per-channel handler,
delegates LLM reasoning to `claude -p` in the right `agents/<role>/` project,
and logs everything to `evidence/`.

## Quickstart

```bash
cd orchestrator
uv venv --python 3.12 .venv
uv pip install -r requirements.txt
```

### Dry run (no token, no live MCP)

Validates wiring; useful in CI and for cold-clone smoke.

```bash
PYTHONPATH=.. .venv/bin/python -m orchestrator.main --dry-run
```

### Tests

```bash
PYTHONPATH=.. .venv/bin/python -m pytest tests
```

15 tests, fully mocked. Should pass on any machine with Python 3.11+.

### Live run

```bash
# from the repo root
set -a; source .env.local; set +a
cd orchestrator
PYTHONPATH=.. .venv/bin/python -m orchestrator.main \
    --scenario launch-day-revenue-engine
```

The orchestrator:

1. Loads `STEPPE_MCP_TOKEN`, `STEPPE_MCP_URL`, optional `TELEGRAM_BOT_TOKEN_OWNER`
   + `TELEGRAM_OWNER_CHAT_ID` from env.
2. Calls `world_start_scenario`.
3. Loops `world_next_event` and dispatches.
4. Writes `evidence/orchestrator-run-<id>.jsonl`.
5. On finish, prints `world_get_scenario_summary`.

### List scenarios

```bash
.venv/bin/python -m orchestrator.main --list-scenarios
```

## Public API

If another module needs MCP access, route through the existing client — do
not introduce ad-hoc HTTP:

```python
from orchestrator.mcp_client import MCPClient

with MCPClient.from_env() as client:
    catalog = client.call_tool("square_list_catalog", {})
```

## See also

- `docs/ARCHITECTURE.md` — system diagram + event flow
- `docs/EVIDENCE-SCHEMA.md` — JSONL line shape
- `docs/MCP-TOOLS.md` — sandbox tool catalog (55 tools)
- `docs/MCP-SETUP.md` — Claude Code `.mcp.json` wiring
