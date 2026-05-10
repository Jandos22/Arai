# T-012 — Production-path doc

> Status: completed. This card was moved from `tasks/INBOX/` to
> `tasks/DONE/` during stale-doc cleanup; the original task brief and
> acceptance checklist are preserved below.

**Owner:** Hermes
**Dependencies:** T-007 + T-008 done (so we can reference all agent boundaries accurately)
**Estimated:** 25 min
**Bonus bucket:** Production readiness (+5 — real-adapter clarity)

## Why

Submission checklist on the team kit page explicitly requires:

> "Clear post-hackathon real-adapter path without exposing credentials."

Right now we don't have this written down. Judges will ding "Prod" score if they can't see HOW Askhat would actually deploy this on Monday with real Square / WhatsApp Business API / Instagram Graph API / Google Business credentials.

## Tasks

Create `docs/PRODUCTION-PATH.md` with these sections:

### 1. From sandbox to real (the swap)

Table mapping every MCP tool we use to the real-world equivalent + auth model:

| Sandbox MCP tool | Real equivalent | Auth |
|---|---|---|
| `square_list_catalog` | Square Catalog API | OAuth access token (Square dashboard) |
| `square_create_order` | Square Orders API | Same OAuth |
| `whatsapp_send` | WhatsApp Cloud API | Phone Number ID + Permanent Access Token (Meta Business) |
| `instagram_send_dm` | Instagram Messaging API | IG Business + Page Access Token |
| `gb_get_metrics` | Google Business Profile API | OAuth (gbp scope) |
| `marketing_create_campaign` | Meta Ads + Google Ads APIs | App + ad-account access tokens |
| `kitchen_create_ticket` | (custom — Notion/Airtable/Sheets) | Choice deferred — recommend Airtable for Askhat |

### 2. Where credentials live

- `.env.local` on Askhat's MacBook ← only place real tokens exist
- Mirrored vault: 1Password "HappyCake Ops" shared with Askhat
- NEVER GitHub (pre-commit hook enforces)
- Credentials rotation: 90 days via Meta + Square dashboards

### 3. The MCP-shape adapter pattern

Show how `orchestrator/mcp_client.py` is the abstraction boundary. Replacement = swap `STEPPE_MCP_URL` env var to a real-MCP-server URL OR write a thin shim that routes calls to real APIs while preserving the JSON-RPC `tools/call` envelope. Either way, agent code (in `agents/sales/`, `agents/marketing/`, `agents/ops/`) doesn't change.

### 4. Deployment steps (what Askhat does Monday)

1. Provision a tiny VM (Hetzner/DO/Railway) — $6/month
2. Install Claude Code CLI + Python 3.11 + Node 22
3. Clone Arai
4. Set up `.env.local` from real-creds vault
5. Set up Telegram webhook → ngrok-or-Cloudflare tunnel → orchestrator
6. Set up WhatsApp Cloud webhook → same tunnel
7. Run `python -m orchestrator.main --live` (no scenario, real time)

### 5. What needs to happen first (before going live)

- WhatsApp Business verification (3-5 day lead time)
- Meta Ads + Google Ads ad accounts billed
- Real Square POS hooked into real menu
- Test on a single product (Medovik) for one week before full rollout

### 6. Risks & rollback

- Single-machine reliability — recommend systemd service + Tailscale for remote access
- Token rotation forgotten — calendar reminder
- Agent over-promises — rate-limit + owner-gate (already designed)
- Rollback: `git checkout v0.x.x` + restart systemd

## Acceptance

- File exists at `docs/PRODUCTION-PATH.md`
- Linked from README.md "Documentation" section
- Linked from SUBMISSION.md as the "post-hackathon real-adapter path" item
- No real credentials anywhere

## Out of scope

- Actually wiring real credentials — that IS the post-hackathon work
- Detailed cost projections — high-level $ ranges only
