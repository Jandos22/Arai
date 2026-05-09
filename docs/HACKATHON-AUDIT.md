# Hackathon Audit — what's actually behind sign-in (2026-05-09 ~14:50 CT)

> Comprehensive audit of every hackathon page reachable on Jandos's signed-in
> Mac mini Chrome. This is the source of truth for what the organizers
> require — supersedes any earlier guesses.

## Pages crawled

| URL | Title | What's there |
|---|---|---|
| `/hackathon` | Agentic AI for real business | Public landing page |
| `/hackathon/brief` | The brief | Full brief (323 lines, also at `/hackathon-assets/HACKATHON_BRIEF.md`) |
| `/hackathon/brief/sandbox` | Sandbox pack | Simulator modules + tool catalog summary + MCP config |
| `/hackathon/brief/assets` | HappyCake assets | 22 photos + 3 logo sizes + metadata.json |
| `/hackathon/teams` | Find a team | Team list — Jan Solo confirmed (captain: Jandos Meirkhan, onsite, 1/3) |
| `/hackathon/teams/<id>/kit` | Team launch kit | **MCP token displayed**, build targets, submission checklist |
| `/hackathon/submit` | Submit | Captain enters repo URL + optional evaluator notes |
| `/hackathon/leaderboard` | Live leaderboard | Empty until 10:00 CT May 10 — **scores 7 dimensions** |

All pages saved as JSON in `/tmp/sbc_audit/*.json` on the Mac mini for re-check.

## Critical finding: leaderboard scores **seven** dimensions, not four

The leaderboard table header is:

> # · Team · **Functional** · **Depth** · **Impact** · **UX** · **Arch** · **Prod** · **Inn** · **Total**

This matches the moderator's description of "7 AI passes" exactly. Our prior assumption — that the 4 `evaluator_score_*` MCP tools (`marketing_loop`, `pos_kitchen_flow`, `channel_response`, `world_scenario`) WERE the scoring loops — was wrong.

The `evaluator_score_*` MCP tools are **what teams use to preview** their work. The actual judging pipeline is 7 AI agents scoring 7 different dimensions each:

| Dimension | What it likely covers (inferred) |
|---|---|
| **Functional** | Does each channel work end-to-end? (Square→kitchen, WA, IG, marketing) |
| **Depth** | Sophistication of agent reasoning, edge-case handling |
| **Impact** | Business value — would Askhat actually use this? |
| **UX** | Customer-facing channel quality + owner-facing Telegram UX |
| **Arch** | System decomposition, visibility, MCP usage, owner-bot mapping |
| **Prod** | Production readiness — clean repo, deploy notes, env model, no secrets |
| **Inn** | Innovation — bonus-style differentiators |

This means our current scoring dashboard (one MCP loop = 100/100) is a **partial** signal, not the full grade. Bonus-plan items map directly into Prod (audit trail, mobile perf, failure handling) and Inn (lead scoring, referrals, follow-ups).

**Action:** update SUBMISSION.md, ARCHITECTURE.md, and BONUS-PLAN.md to reflect this. Don't promise a 4-loop max — the real ceiling is broader.

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
- `hero/hero-{01..04}.webp` — 1600×1000 lifestyle hero shots
- `products/product-{01..10}.webp` — 1200×1200 product cake photos
- `social/social-{01..04}.webp` — 1080×1350 social/IG crops
- `logo/logo-{256,512,1024}.png`
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

Token: `sbc_team_18b…` (full token visible only on the kit page; lives in MacBook `.env.local`, never committed).

**Tools listed in kit (from kit page narrative):**
> Start your demand engine with `marketing_create_campaign`, then launch, generate leads, route them, adjust, and report back to the owner. Validate production promises with `kitchen_create_ticket`, capacity checks, accept/reject decisions, and ready-for-pickup status. Use `square_create_order` and `square_get_pos_summary` to prove your website and agents can drive POS-style orders. Run `world_start_scenario` and `world_next_event` to test against the same time-compressed business day as the evaluator. Use `evaluator_get_evidence_summary` and `evaluator_generate_team_report` to preview the evidence judges will inspect.

This **confirms our approach end-to-end** — every tool we already use is the right one. No surprises.

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
| 3 | Update SUBMISSION.md to reference 7 leaderboard dims | Hermes | TODO |
| 4 | Update ARCHITECTURE.md: 4 MCP loops are PREVIEW, not all of grade | Hermes | TODO |
| 5 | Wire real cake photos into website pages | Hermes | TODO (T-009b) |
| 6 | Add "post-hackathon real-adapter path" doc | Hermes | TODO (T-009c) |
| 7 | Add complaint / custom-cake consultation paths to sales | CC | TODO (bonus item) |
