# Production path — from sandbox to real Happy Cake

> **Audience:** Askhat + a future engineer onboarding this stack.
> **Status:** post-hackathon roadmap. Nothing here runs against real
> credentials yet.
>
> The hackathon brief grades teams on whether the system can be brought
> "close to a real Happy Cake deployment." This doc is that path —
> concrete, sequenced, no hand-waving.

## TL;DR

Going live = swap the **MCP endpoint URL + token**, plug in **real-API
adapters** behind the same MCP-shape interface, run the **same
orchestrator + same agents + same Telegram bot wrappers** unchanged. We
designed the system around this swap — `orchestrator/mcp_client.py` is
the single chokepoint between the agentic logic and the world.

```
           ┌─────────────────────────────────────────────┐
           │  AGENT LAYER                                │
           │  agents/sales/  agents/marketing/  ops/     │
           │  Telegram bots  Orchestrator scenario loop  │
           │  (CHANGES NOTHING between sandbox and prod) │
           └─────────────────────┬───────────────────────┘
                                 │ JSON-RPC tools/call
                                 ▼
           ┌─────────────────────────────────────────────┐
           │  MCP CLIENT  (orchestrator/mcp_client.py)   │
           └─────────────────────┬───────────────────────┘
                                 │
       ┌─────────────────────────┴────────────────────────┐
       ▼ HACKATHON                                        ▼ PRODUCTION
  www.steppebusinessclub.com/api/mcp        Real-adapter MCP server
  (Steppe sandbox simulator)                (we own; thin wrapper around real APIs)
                                                          │
                          ┌───────────────────────────────┼─────────────────────┐
                          ▼                               ▼                     ▼
                    Square POS API              WhatsApp Cloud API     Meta Ads + GBP APIs
```

The agent layer never knows whether it's hitting the sandbox or production.

## 1. The swap, tool by tool

Every MCP tool we use today maps to a real-world equivalent. Auth model
is the column to focus on — that's what determines what Askhat needs
from each platform vendor.

| Sandbox MCP tool | Real-world equivalent | Auth | Lead time |
|---|---|---|---|
| `square_list_catalog` | [Square Catalog API](https://developer.squareup.com/reference/square/catalog-api) | OAuth access token (Square dashboard) | hours |
| `square_create_order` | Square Orders API | same | — |
| `square_update_order_status` | Square Orders API | same | — |
| `square_get_pos_summary` | Square Reports API + custom rollup | same | — |
| `square_recent_sales_csv` | Square Sales report export | same | — |
| `square_get_margin_by_product` | derived from Square + cost-of-goods spreadsheet | manual reconcile | low |
| `whatsapp_send` | [WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api) `messages` POST | Phone Number ID + permanent System User token (Meta Business Manager) | **3–5 days** (WA Business verification) |
| `whatsapp_inject_inbound` (sandbox) | WhatsApp webhook subscription on the Phone Number ID | webhook verify token | included in WA setup |
| `instagram_send_dm` | [IG Messaging API](https://developers.facebook.com/docs/messenger-platform/instagram) | IG Business + Page access token (linked Facebook Page required) | hours after FB Page wired |
| `instagram_reply_to_comment` | IG Graph API `comments` endpoint | same Page access token | — |
| `instagram_schedule_post` + `instagram_publish_post` | IG Graph API `media` + `media_publish` | same | — |
| `gb_get_metrics` | [Google Business Profile API](https://developers.google.com/my-business) | OAuth (`business.manage` scope) | hours |
| `gb_reply_review` | GBP API `reviews/reply` | same | — |
| `kitchen_create_ticket` + `kitchen_*` family | **No vendor — we host this.** Recommendation: Airtable, Notion DB, or a lightweight Postgres + a kitchen-facing iPad PWA. | API key for chosen tool | hours |
| `marketing_create_campaign` + `launch_simulated_campaign` | **Two real APIs.** Meta Ads (Facebook + IG) → [Marketing API](https://developers.facebook.com/docs/marketing-apis); Google Ads → [Ads API](https://developers.google.com/google-ads/api). | App + ad-account access tokens, possibly app review | 1–2 weeks for app review on Meta |
| `marketing_generate_leads` | Meta Lead Ads webhooks + Google Ads conversion uploads | same | — |
| `marketing_get_budget` + `marketing_get_margin_by_product` | reads from Square + ad-platform reporting | same | — |
| `marketing_report_to_owner` | **No vendor — Telegram bot, already built** (orchestrator's owner-notifier) | TELEGRAM_BOT_TOKEN_OWNER | 5 min |
| `world_*` (scenario, time, evidence) | **Sandbox-only.** Production = real time, real events. The orchestrator just polls the real webhooks instead of `world_next_event`. | n/a | n/a |
| `evaluator_*` | **Sandbox-only.** Replaced in production by ops dashboards + monthly KPI rollup. | n/a | n/a |

### Critical-path summary

The slowest item is **WhatsApp Business verification (3–5 days)**. Start
that the day Askhat decides to go live. Everything else can be wired
concurrently.

## 2. Where credentials live

```
Askhat's MacBook
└── ~/dev/Arai/.env.local          ← only place real tokens exist
    ├── STEPPE_MCP_TOKEN           (sandbox, retire post-launch)
    ├── PROD_MCP_URL               (our real-adapter endpoint)
    ├── PROD_MCP_TOKEN             (rotates every 90 days)
    ├── SQUARE_ACCESS_TOKEN
    ├── WA_PHONE_NUMBER_ID
    ├── WA_PERMANENT_TOKEN
    ├── IG_PAGE_ACCESS_TOKEN
    ├── GBP_REFRESH_TOKEN
    ├── META_ADS_ACCESS_TOKEN
    ├── GOOGLE_ADS_DEVELOPER_TOKEN + REFRESH_TOKEN
    └── TELEGRAM_BOT_TOKEN_OWNER + TELEGRAM_OWNER_CHAT_ID

1Password vault: "HappyCake Ops"
└── shared with: Askhat (owner), engineer-on-call
└── mirrors all of the above; .env.local is a write-down from the vault

GitHub: NEVER. Pre-commit hook in scripts/git-hooks/pre-commit blocks
real-token patterns. .env, .env.local, .env.*.local are gitignored.
```

**Rotation cadence:**
- Square OAuth: 30 days (Square enforces); auto-refresh via stored refresh token
- WA permanent token: never expires *but* rotate on staff change (System User token)
- IG/FB Page tokens: 60 days (Meta enforces); long-lived flow yields 60-day token
- Google Ads/GBP refresh tokens: never expire; revoke + re-OAuth on staff change
- `PROD_MCP_TOKEN`: 90 days, rotated by us
- Calendar reminder on Askhat's phone for each rotation date

## 3. The MCP-shape adapter pattern

Why we didn't write production code directly: the brief constrains
runtime to Claude Code CLI + MCP. Plus, decoupling the agent from real
APIs means we can swap implementations without touching prompts or
flows.

The real-adapter MCP server is a small Python + FastMCP project we'll
write post-hackathon. It exposes the **same tool names + same JSON
shapes** as the sandbox, so our `agents/sales/.mcp.json` etc. just point
at a different URL with a different token. **No agent code changes.**

```python
# Conceptual — production MCP adapter, sketched.
# Lives in a separate repo: happycake-mcp-adapter
from fastmcp import FastMCP
import square, requests

app = FastMCP("happycake-prod")

@app.tool()
def square_list_catalog():
    """Drop-in replacement for sandbox tool — returns same shape."""
    raw = square_client.catalog.list()
    return {"items": [_normalize(item) for item in raw.objects]}

@app.tool()
def whatsapp_send(to: str, message: str):
    r = requests.post(
        f"https://graph.facebook.com/v21.0/{WA_PHONE_NUMBER_ID}/messages",
        headers={"Authorization": f"Bearer {WA_TOKEN}"},
        json={"messaging_product": "whatsapp", "to": to, "type": "text",
              "text": {"body": message}},
    )
    r.raise_for_status()
    return {"messageId": r.json()["messages"][0]["id"], "to": to}
```

Hosting: tiny VM (Hetzner CX11 / DO basic / Railway $5 plan). Behind a
TLS-terminated reverse proxy. Cloudflare Tunnel is fine for the
MacBook-direct path, but for production we want a proper VM so the
system survives Askhat's MacBook sleeping.

## 4. Deployment steps — what Askhat does on go-live day

```bash
# 0. PREREQUISITE: WhatsApp Business verification done (T-3 days minimum)

# 1. Provision tiny VM (Hetzner CX11 = €4.50/mo)
ssh root@happycake-prod "apt update && apt install -y python3.12 git nodejs nginx"

# 2. Install Claude Code CLI on the VM
curl -fsSL https://claude.ai/install.sh | bash

# 3. Clone Arai + the new real-adapter MCP server
git clone git@github.com:Jandos22/Arai.git
git clone git@github.com:Jandos22/happycake-mcp-adapter.git

# 4. Real-adapter setup
cd happycake-mcp-adapter
cp .env.example .env.local
# (fill in real tokens from 1Password)
pip install -r requirements.txt
systemctl enable --now happycake-mcp-adapter

# 5. Arai orchestrator points at real adapter
cd ../Arai
cp .env.example .env.local
# Set: STEPPE_MCP_URL=https://mcp.happycake.us/api/mcp
# Set: STEPPE_MCP_TOKEN=<prod-token-from-vault>
# Set: TELEGRAM_BOT_TOKEN_OWNER + TELEGRAM_OWNER_CHAT_ID
cd orchestrator && uv venv .venv && uv pip install -r requirements.txt
systemctl enable --now arai-orchestrator

# 6. Webhook tunnels: WhatsApp → adapter, Instagram → adapter
# Configure in Meta Business Manager:
#   WhatsApp webhook URL: https://mcp.happycake.us/wa/webhook
#   IG webhook URL:       https://mcp.happycake.us/ig/webhook
# Both with the verify token we set in .env.local

# 7. Smoke test
bash scripts/e2e_smoke.sh    # against sandbox first, prove unchanged
bash scripts/prod_smoke.sh   # against prod adapter (TBW post-hackathon)

# 8. Soft launch — one product (Medovik) for one week before full rollout
```

Everything runs as a systemd service. Logs to `/var/log/arai/` +
`evidence/*.jsonl` for the audit trail. Tailscale for Askhat's remote
access from his iPhone.

## 5. What needs to happen before going live

**Pre-flight checklist (gated):**

- [ ] **WhatsApp Business verified** (3–5 day lead — start here)
- [ ] Square POS account upgraded to support API access (free, instant)
- [ ] Instagram Business account linked to a Facebook Page
- [ ] Google Business Profile claimed and verified
- [ ] Meta Ads account funded (any amount; tokens require live account)
- [ ] Google Ads account opened + funded
- [ ] All credentials written into `.env.local` from 1Password
- [ ] `bash scripts/e2e_smoke.sh` against sandbox still PASS (regression net)
- [ ] `bash scripts/prod_smoke.sh` against real adapter passes (single-product test)
- [ ] Telegram bot deployed, Askhat receives and acts on a test approval
- [ ] One full week of soft-launch with **Medovik only**, ≤10 orders/day
- [ ] Owner-gate triggers reviewed by Askhat manually for the first 100 orders
- [ ] Refund / complaint flow tested on a synthetic complaint
- [ ] Monitoring: orchestrator process alive check + Telegram heartbeat every 6h

**Don't go live without:**
- WA Business verification (legal/policy)
- Square + Telegram bot working in dry-run
- 1Password vault shared with one backup person
- A documented "off switch" — `systemctl stop arai-orchestrator` shuts the
  agent down without breaking the bakery's manual ops fallback (Askhat
  can still answer WhatsApp himself if the bot is down)

## 6. Risks & rollback

| Risk | Mitigation | Rollback |
|---|---|---|
| Single-machine reliability | systemd + monitoring + Tailscale; small VM is cheap to replicate | manual ops fallback always works |
| Token rotation forgotten | Calendar reminders on Askhat's phone; quarterly review | grace period: 7 days notice from each platform before token expires |
| Agent over-promises (capacity, allergens) | Owner-gate triggers + `kitchen_get_capacity` checks already enforced in `agents/sales/policies/owner_gate_rules.md` | Askhat's manual override; complaint flow handles fallout |
| Customer escalates publicly (IG/GMB review) | Sales agent escalates via Telegram on emotional cues (already in policies); ops agent flags negative reviews | Askhat replies personally; system never publishes a review reply without approval |
| Agent sends wrong customer the wrong message | Per-message audit trail in `evidence/*.jsonl`; idempotency keys on outbound; brand-voice rate-limit | Replay log; apologize; refund |
| MCP adapter goes down | Health check + Telegram alert; auto-restart via systemd | Manual ops while it's down; webhooks queue at platform side for ~24h |
| Cost overrun on ad spend | `marketing_get_budget` returns hard cap; budget enforced in agent prompt | Pause campaigns via Telegram `/marketing_pause` |
| Real allergen mistake → health incident | Allergy-safe communication path (T-013) routes ALL allergy claims through owner-gate; structured allergens in `/api/catalog`; complaint flow logs + escalates | Refund + apology + manual review of all allergy-flagged orders for previous 7 days |
| Pre-commit hook bypassed → token leak | `scripts/git-hooks/pre-commit` plus weekly `git log -p` token-scan cron | Rotate token; audit log review |

**Rollback procedure:**

```bash
# Soft rollback — orchestrator only, manual ops resumes
ssh root@happycake-prod "systemctl stop arai-orchestrator"

# Hard rollback — revert to previous Arai version
ssh root@happycake-prod
cd /opt/arai
git fetch origin
git checkout v0.<previous-tag>
systemctl restart arai-orchestrator

# Nuclear — disable adapter, fall back fully to manual
systemctl stop arai-orchestrator happycake-mcp-adapter
# Remove webhook URLs in Meta Business Manager so customers' WA messages
# go nowhere automated; Askhat answers them on his phone.
```

## 7. Post-launch maintenance budget

- **Engineer time:** ~4h/week for the first month (token rotations, fixing
  edge cases, adjusting prompts based on real customer messages)
- **Cost:** VM + domain + Cloudflare = ~$15/mo. Marketing budget separate.
- **Code changes:** prompts evolve faster than infrastructure. Expect to
  edit `agents/*/CLAUDE.md` weekly for the first month, monthly thereafter.

## 8. The "first hire" moment

When Askhat hires the first ops person, they get:
- Their own Telegram bot subscription (forwarded approval messages)
- Read-only repo access (no write to `agents/`)
- Onboarding via this doc + `docs/DEMO.md`
- Shadowing one week of approvals before deciding alone

The system is designed for one operator → small team transition without
re-architecture. Multi-operator = same Telegram bot, multiple chat IDs.

---

**Maintenance owner:** Jandos (initial), then Askhat's chosen engineer.
Last revised: 2026-05-09 (hackathon submission day).
