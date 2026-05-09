# Bonus Plan — Going for 115/100

> **Source:** `docs/HACKATHON_BRIEF.md` §9 "Bonus points" (added by mods on 2026-05-09 mid-hackathon).
> **TL;DR:** Core score is 100. Bonus adds up to **+15** if the team solves additional Happy Cake business pains. Cap = **115**.

## Bonus gating

| Core score | Bonus eligibility |
|---|---|
| 80+ | up to **+15** |
| 60–79 | max **+5** |
| <60 | none |

So bonus only matters if the core is strong. **Step 1 is locking core ≥ 80.** Then we go for the +15.

## Three bonus buckets (up to +5 each)

### A. Real business pain (+5)
- custom cake intake
- complaints / refunds
- allergy-safe communication
- production capacity
- repeat customers
- reviews
- abandoned orders

### B. Production readiness (+5)
- clean deploy
- mobile performance
- admin / operator view
- audit trail
- failure handling
- safe owner handoff

### C. Growth upside (+5)
- lead scoring
- local SEO
- referrals
- WhatsApp follow-up
- upsell logic
- marketing budget optimization

## What we already have (preliminary scoring)

| Bucket | Item | State | Notes |
|---|---|---|---|
| A | custom cake intake | 🟡 partial | sales agent supports it; no dedicated intake form on site |
| A | complaints / refunds | ❌ | not built |
| A | allergy-safe communication | 🟡 brand-voice yes | no structured allergen flag in catalog/JSON-LD |
| A | abandoned orders | ❌ | not built |
| A | reviews | 🟡 covered by T-007 (GMB) | depends on what CC ships |
| B | clean deploy | 🟢 | website builds clean (`scripts/test_website.sh`) |
| B | mobile performance | 🟡 untested | Next.js static, should pass; no Lighthouse yet |
| B | admin / operator view | 🟢 | Telegram bots = the operator view; this is the spec |
| B | audit trail | 🟢 | `evidence/` JSONL writer per `EVIDENCE-SCHEMA.md` |
| B | failure handling | 🟡 partial | MCP retries done; agent-level fallback not yet |
| B | safe owner handoff | 🟢 | T-003 approval queue + T-005 owner-gate + T-006 owner reports |
| C | lead scoring | ❌ | T-006 routes leads but doesn't score |
| C | local SEO | 🟡 | JSON-LD shipped; missing `LocalBusiness` schema |
| C | referrals | ❌ | not built |
| C | WhatsApp follow-up | ❌ | not built (sales agent answers but doesn't follow up) |
| C | upsell logic | ❌ | not built |
| C | marketing budget optimization | 🟢 | **T-006 100/100, this is exactly the bonus** |

## High-leverage low-cost adds (rank-ordered)

These are the ones with the best points-per-hour ratio. Pick the top 3 once core is solid.

1. **`LocalBusiness` JSON-LD on website homepage** (~10 min) — checks "local SEO" in bucket C. Hermes-owned.
2. **Allergen flags in catalog + `/api/catalog`** (~20 min) — checks "allergy-safe communication" in bucket A. Hermes-owned.
3. **Custom cake intake page on website** (~30 min) — `/custom-cake` form posting to `/api/custom-cake-request`, hands off to owner via Telegram. Bucket A. Hermes-owned.
4. **WhatsApp follow-up cron in orchestrator** (~30 min) — for any order in `pending_pickup` state, send a polite "we'll see you at X" note 2h before. Bucket C. Hermes-owned.
5. **Lead scoring in marketing agent** (~30 min) — score 0–100 based on channel, intent strength, repeat-customer flag. Bucket C. CC-owned (touches `agents/marketing/`).
6. **Complaints / refunds path in sales agent** (~30 min) — detect complaint intent, route to owner-gate with full context. Bucket A. CC-owned (touches `agents/sales/`).
7. **Lighthouse mobile run + capture screenshot** (~15 min) — proves "mobile performance" claim. Hermes-owned.
8. **Failure-handling block in each agent CLAUDE.md** (~15 min) — explicit "if MCP errors, do X" rules, plus an injected error in the smoke. Bucket B. CC-owned.

## Strategy

- **Right now:** finish core (T-007 ops + T-008 e2e). Don't go for bonus until core demos cleanly end-to-end.
- **Once T-008 passes:** run `evaluator_preview.sh` to confirm core ≥ 80.
- **If yes:** sequence the top 3 bonus items above (Hermes 1+2 in parallel with CC's bonus item, then 3 if time).
- **If no:** fix what's blocking core score; bonus is wasted effort below 80.

## Bonus is a leaderboard tiebreaker

Even if multiple teams hit ~95 core, the +15 ceiling is the difference between 1st ($3000) and 2nd ($1000). It's worth real effort once core is locked.
