# Arai

AI sales + ops system for **Happy Cake US** (Sugar Land, TX).
Built for the **Steppe Business Club Hackathon** — May 9–10, 2026.

**Team:** Jan Solo — Jandos Meirkhan (captain), augmented by Hermes (project manager AI) and Claude Code (agent runtime).
**Submission deadline:** May 10, 2026, 10:00 CT.

## What this is

A vertical slice that takes a customer from interest → order → kitchen handoff → owner approval, plus an agent-readable storefront and a $500/mo marketing plan. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the design and [`CLAUDE.md`](CLAUDE.md) for the team contract.

## Quickstart (fresh clone)

```bash
git clone https://github.com/Jandos22/Arai.git
cd Arai
cp .env.example .env.local
# → fill in STEPPE_MCP_TOKEN (from your team launch kit) and Telegram bot tokens

# website
cd website && npm install && npm run dev

# bots
cd ../bots && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python router.py
```

## Key docs

- [`CLAUDE.md`](CLAUDE.md) — team contract, ownership, hard rules
- [`docs/HACKATHON_BRIEF.md`](docs/HACKATHON_BRIEF.md) — original hackathon brief
- [`docs/brand/HCU_BRANDBOOK.md`](docs/brand/HCU_BRANDBOOK.md) — Happy Cake brand book
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system design (TBD)
- [`docs/MCP-TOOLS.md`](docs/MCP-TOOLS.md) — sandbox tool catalog (populated in T-001)
- [`docs/MARKETING.md`](docs/MARKETING.md) — $500/mo marketing case (TBD)
- [`tasks/`](tasks) — task briefs (INBOX → DOING → DONE)

## Security

**Never commit** `.env.local`, `STEPPE_MCP_TOKEN`, Telegram bot tokens, or any secret. `.gitignore` blocks the obvious. If a token leaks, ping organizers immediately for rotation.
