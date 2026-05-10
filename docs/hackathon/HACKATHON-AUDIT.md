# Hackathon Audit — what's actually behind sign-in (2026-05-09, refreshed ~21:30 CT)

> Comprehensive audit of every hackathon page reachable on Jandos's signed-in
> Mac mini Chrome. This is the source of truth for what the organizers
> require — supersedes any earlier guesses.

## Pages crawled

| URL | Title | What's there |
|---|---|---|
| `/hackathon` | Agentic AI for real business | Public landing page |
| `/hackathon/register` | Register | Registration route linked from public landing page |
| `/hackathon/brief` | The brief | Full brief (323 lines, also at `/hackathon-assets/HACKATHON_BRIEF.md`) |
| `/hackathon/brief/sandbox` | Sandbox pack | Simulator modules + tool catalog summary + MCP config |
| `/hackathon/brief/assets` | HappyCake assets | 22 photos + 3 logo sizes + metadata.json |
| `/hackathon/teams` | Find a team | Team list — Jan Solo confirmed (captain: Jandos Meirkhan, onsite, 1/3) |
| `/hackathon/teams/<id>/kit` | Team launch kit | **MCP token displayed**, build targets, submission checklist |
| `/hackathon/submit` | Submit | Captain enters repo URL + optional evaluator notes |
| `/hackathon/leaderboard` | Live leaderboard | Empty until 10:00 CT May 10 — **scores 7 official weighted passes** |

First pass pages were saved as JSON in `/tmp/sbc_audit/*.json` on the Mac mini.
The later Chrome re-check is summarized from `.gstack/browse-audit.jsonl`,
`.gstack/browse-network.log`, and the browser-visible pages listed above.

## 2026-05-09 late source-route re-check

Fresh Chrome coverage confirmed the route set from the first pass and added
explicit evidence boundaries for assets and remaining gaps:

| Source route / artifact | Evidence supplied | Notes |
|---|---|---|
| `/hackathon` | Public judging model, registration/brief/team links | Network log shows the route loaded successfully at 2026-05-09 21:06 CT. |
| `/hackathon/register` | Registration route exists and is linked | The re-check only needed route coverage; no private registration payload is copied here. |
| `/hackathon/brief` | Current brief text and links to sandbox/assets | `docs/hackathon/HACKATHON_BRIEF.md` remains the repo copy for source alignment. |
| `/hackathon/brief/sandbox` | Sandbox modules, runtime rules, MCP/evaluator preview framing | This continues to support the architecture decision that the MCP sandbox is source of truth. |
| `/hackathon/brief/assets` | Rendered HappyCake asset inventory page | This page, plus `metadata.json`, is the safe evidence source for asset counts and rules. |
| `/hackathon-assets/happy-cake/metadata.json` | Private source inventory metadata | Browser history shows the metadata URL was opened; repo copy records 562 source images, 2 zips, and the curated export rules. |
| `/hackathon-assets/happy-cake/<raw originals>` | Not used as repo evidence | Treat raw original JPG/ZIP URLs as client-blocked/private source material. The repo must use only curated `website/public/brand/**` exports. |
| `/hackathon/teams` | Team list / competitive landscape | Do not copy private account details beyond high-level team observations. |
| `/hackathon/teams/<id>/kit` | Team-specific token, tool list, submission checklist | Token and private kit identifiers stay redacted. Only the tool categories and checklist are summarized below. |
| `/hackathon/submit` | Required public repo URL and optional notes field | Confirms the final submission mechanics. |
| `/hackathon/leaderboard` | Live scoring surface | Confirms public leaderboard exists; official scoring still maps to the seven weighted passes below. |

### Asset mismatch now documented

The re-check exposed an important distinction: the source asset system has a
large private inventory, while this repo intentionally carries only a curated
web-ready subset.

| Asset source | Count / contents | Status in repo |
|---|---:|---|
| Steppe private source inventory (`metadata.json`) | 562 source images, 2 zips, 1 logo PNG, ~8.27 GB raw bytes | Not committed and not linked from public pages |
| Rendered `/hackathon/brief/assets` page | 22 photos + 3 logo sizes + metadata | Used as crawl evidence |
| `website/public/brand/` curated export | 4 hero images, 10 product images, 8 social crops, 3 logo PNGs, metadata | Committed, optimized, safe for Next.js public serving |

Raw originals referenced by metadata `sourceId` values, such as `1V8A9769.jpg`,
stay private. The app should keep serving only the curated filenames under
`website/public/brand/`, and docs should avoid source filesystem paths or raw
download URLs.

### Gap table from the latest crawl

| Gap from crawl | Evidence | Tracking |
|---|---|---|
| Audit doc lagged behind late Chrome re-check | This file did not previously include `/hackathon/register`, asset mismatch, or route-to-evidence mapping | [GitHub issue #20](https://github.com/Jandos22/Arai/issues/20) |
| Website README was stale against current website behavior | Re-check noted README risk; current `website/README.md` now documents agent-readable endpoints, order-intent, assistant, and curated asset rules | Covered in repo docs; no token/private detail needed |
| Mobile/performance proof still needed | Production-readiness bonus rewards mobile-ready storefront proof | [GitHub issue #8](https://github.com/Jandos22/Arai/issues/8) |
| Google Business local simulator coverage is thin | Sandbox includes Google Business local/review/post/metrics capabilities beyond current smoke proof | [GitHub issue #19](https://github.com/Jandos22/Arai/issues/19) |
| Growth bonus features remain partial | Lead scoring, referrals, follow-up, abandoned orders are explicitly bonus-relevant | [GitHub issue #22](https://github.com/Jandos22/Arai/issues/22) |
| Telegram bot registration is operational, not code-only | Operator simulator expects owner/bot interaction; tokens must stay local | [GitHub issue #10](https://github.com/Jandos22/Arai/issues/10) |
| Final dress rehearsal still pending | Submission requires clean clone, tests, evaluator preview, leak scan, final push | [GitHub issue #4](https://github.com/Jandos22/Arai/issues/4) |

## Critical finding: official judging is **seven weighted passes**, not four preview loops

The public hackathon page lists seven official judging passes with weights:

| Official pass | Weight | What it covers for Arai |
|---|---:|---|
| **Functional scenario tester** | **20** | Drives simulated customer scenarios across WhatsApp, Instagram, and the website. Public scenarios are practice; secret ones decide. |
| **Agent-friendliness auditor** | **15** | Agent-readable website, structured catalog/policies, autonomous order-intent path, clear machine contracts |
| **On-site assistant evaluator** | **15** | Consultation, custom order, complaint/status handling, escalation quality, owner/customer UX |
| **Code reviewer** | **10** | Repo clarity, scoped agents, tests, security hygiene, readable architecture |
| **Operator simulator** | **15** | Owner controls, Telegram approval flow, capacity decisions, operational usefulness during a live day |
| **Business analyst** | **15** | $500-to-$5K case, campaign math, revenue impact, production adoption path |
| **Innovation/depth spotter** | **10** | Differentiators beyond the brief: agent-readable storefront, scoped MCPs, safety gates, bonus paths |

Our prior assumption — that the 4 `evaluator_score_*` MCP tools (`marketing_loop`, `pos_kitchen_flow`, `channel_response`, `world_scenario`) WERE the scoring loops — was wrong.

The `evaluator_score_*` MCP tools are **what teams use to preview** their work. They are not the full grade. The official grade is a weighted 100-point total across the seven passes above:

- Functional scenario tester: 20%
- Agent-friendliness auditor: 15%
- On-site assistant evaluator: 15%
- Code reviewer: 10%
- Operator simulator: 15%
- Business analyst: 15%
- Innovation/depth spotter: 10%

This means our current scoring dashboard (one MCP loop = 100/100) is a **partial** signal, not the full grade. Bonus-plan items map directly into operator usefulness, business analysis, and innovation/depth (audit trail, mobile perf, failure handling, lead scoring, referrals, follow-ups).

The public page also confirms the bonus model: 100 core points, up to +15
bonus points, maximum total score 115. Core 80+ is eligible for up to +15,
core 60–79 is capped at +5, and core below 60 gets no bonus.

**Action:** keep SUBMISSION.md, SELF-EVAL.md, and ARCHITECTURE.md aligned to these official weighted passes. Don't promise a 4-loop max — the real ceiling is broader.

## Critical finding: build target #1 is "the website becomes the future production happycake.us"

From `/hackathon/brief/sandbox`:

> **Website as production artifact:** the winning website is expected to become the future production happycake.us after the hackathon. Build it as a real sales system, not a mockup.

This is a much stronger signal than "agent-friendly storefront." Our website needs to look and behave like something Askhat would actually deploy on Monday — that means:
- Real cake photos (now pulled into `website/public/brand/`)
- Real prices, real lead times, real allergens
- Mobile-first UX (Lighthouse-tested)
- Working order-intent flow that lands somewhere meaningful (kitchen ticket via MCP)
- SEO-visible (LocalBusiness schema, Open Graph, sitemap)

## Asset pack — pulled

`website/public/brand/`:
- `hero/happy-cake-hero-{01..04}.webp` — 1600×1000 lifestyle hero shots
- `products/happy-cake-product-{01..10}.webp` — 1200×1200 product cake photos
- `social/happy-cake-social-{01..08}.webp` — 1080×1080 social crops
- `logo/happy-cake-logo-{256,512,1024}.png`
- `metadata.json` — describes every file + palette + usage rules

**Asset rules** (from metadata.json):
- raw originals are NOT copied into the app repo public folder
- do NOT expose local filesystem paths
- publish only after launch approval (we're past launch — fine)

**Brand palette in metadata** (lighter/simpler version of brandbook):
- Happy Sky Blue `#00AEEA` (primary CTA)
- Chocolate Brown `#6B3A1E` (wordmark)
- Vanilla Cream `#FFF7EA` (backgrounds)
- Bakery White `#FFFFFF`
- Berry Accent `#E94B7B` (sparingly — promos, social)

**Our Tailwind palette uses the BRANDBOOK §4 palette** (deeper Happy Blue family + cream + coral/green seasonals). The brandbook is canonical per the brief; metadata.json is a simplified subset. **Decision: keep brandbook palette, but mention metadata as cross-reference.**

## Submission flow — confirmed

`/hackathon/submit`:
- Form with one required field: **Public Git repository URL**
- Optional field: **Notes for the evaluator**
- "Save submission" button
- Updateable until 10:00 CT May 10
- Must be public (evaluator clones directly)

**Captain (Jandos) submits.** Repo URL: `https://github.com/Jandos22/Arai`.

## Team kit — token + tool list confirmed

Token: `<redacted>` (full token visible only on the kit page; lives in MacBook `.env.local`, never committed).

**Tools listed in kit (from kit page narrative):**
> Start your demand engine with `marketing_create_campaign`, then launch, generate leads, route them, adjust, and report back to the owner. Validate production promises with `kitchen_create_ticket`, capacity checks, accept/reject decisions, and ready-for-pickup status. Use `square_create_order` and `square_get_pos_summary` to prove your website and agents can drive POS-style orders. Run `world_start_scenario` and `world_next_event` to test against the same time-compressed business day as the evaluator. Use `evaluator_get_evidence_summary` and `evaluator_generate_team_report` to preview the evidence judges will inspect.

This **confirms our approach end-to-end** — every tool we already use is the right one. No surprises.

## Adversarial check: implement Cloudflare Tunnel webhook path

Issue #9 challenged whether skipping ngrok could be a hidden DQ or scoring
risk because current brief §04 says "Every team will end up with something
like this" and shows "WhatsApp / IG webhook hits ngrok URL" as step 1.
Strongest case against us: the channel-behavior criterion might expect a
public webhook path, and a judge doing a literal read of §04 could mark a
sandbox-polling loop as less faithful to the standard runtime pattern.

Updated decision after re-reading current brief §03 screenshot: implement a
thin Cloudflare Tunnel webhook path before submission. §03 includes "Inbound
webhooks tunnel home" under hard rules and says violations are disqualified.
Even though real WhatsApp/Instagram production access remains forbidden and §06
keeps the sandbox as source of truth, we should demonstrate the required
runtime shape with sandbox/test webhook payloads.

Scope: add a local HTTP wrapper, expose it through Cloudflare Tunnel, and route
`POST /webhooks/whatsapp` and `POST /webhooks/instagram` into the existing
orchestrator dispatcher. The adapter should log evidence, support a dry-run
health endpoint, and be registerable with the sandbox MCP
`whatsapp_register_webhook` / `instagram_register_webhook` tools once a public
Tunnel URL exists. No real Meta credentials or production customer messages are
needed.

## Submission checklist — verbatim from kit page

- [x] Public GitHub repo with final commit before deadline
- [x] README with clean setup from a fresh clone
- [x] ARCHITECTURE.md explaining agents, routing, owner controls, and MCP usage
- [x] `.env.example` with placeholders only, no secrets
- [x] Website/storefront instructions and production-deploy notes
- [x] Agent-friendliness notes: readable catalog/policies, autonomous ordering path, status lookup
- [x] On-site assistant test script: consultation, custom order, complaint, status, escalation
- [x] Marketing, channel, POS, and kitchen scenarios documented with expected behavior
- [x] Evidence of tests, smoke checks, or scripted demos
- [x] Clear post-hackathon real-adapter path without exposing credentials

We tick most of these already. Missing pieces:
- "On-site assistant test script: consultation, custom order, complaint, status, escalation" — sales smoke covers WA + owner-gate, but not specifically a custom-cake consult or complaint flow. **Bonus item from BONUS-PLAN.md aligns.**
- "Clear post-hackathon real-adapter path" — should add a brief section to ARCHITECTURE.md or a `docs/PRODUCTION-PATH.md`.

## Other teams (competitive landscape)

From `/hackathon/teams`:
- Total ~17 visible teams. Most 1/3 — solo applicants. A handful of full 3/3 teams (VVERH PO ROZYBAKIYEVA, Leader XXI = 3 Austin engineers).
- Mix of onsite (Almaty) and online.
- Strong-signal teams: ParkFlow ("AI/IoT/high-perf backend"), DaAr ("real AI products, not just demos"), dust2ai ("Senior AI Engineer").
- Nurlan's Kairo team — that's the "off-topic Nurlan" the moderator mentioned (Silk Road / SBC network, not a real competitor but graded same).

## Action items from this audit

| # | Action | Owner | Status |
|---|---|---|---|
| 1 | Pull asset pack into `website/public/brand/` | Hermes | ✅ done |
| 2 | Save this audit doc | Hermes | ✅ this file |
| 3 | Update SUBMISSION.md to reference 7 official weighted passes | Hermes | ✅ done |
| 4 | Update ARCHITECTURE.md: 4 MCP loops are PREVIEW, not all of grade | Hermes | ✅ done |
| 5 | Wire real cake photos into website pages | Hermes | ✅ done |
| 6 | Add "post-hackathon real-adapter path" doc | Hermes | ✅ done |
| 7 | Add complaint / custom-cake consultation paths to sales | CC | ✅ done |
