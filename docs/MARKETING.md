# MARKETING.md — the $500 case for HappyCake

> Single-cycle plan for one $500 monthly marketing budget. Every number below
> comes from a sandbox MCP tool the agent actually called this run; nothing
> here is invented. See **Methodology note** at the end.

## Inputs

- **Monthly budget:** $500 (target effect $5,000) — `marketing_get_budget`.
- **Recent revenue (last 6 months):** Nov 2025 $14,820 / 612 orders →
  Dec 2025 $19,240 / 738 → Jan 2026 $15,110 / 621 → Feb 2026 $16,890 / 668 →
  Mar 2026 $17,640 / 691 → Apr 2026 $18,320 / 724 — `marketing_get_sales_history`,
  cross-checked against `square_recent_sales_csv`.
- **Average ticket (Apr 2026):** $25.30. Six-month range $24.22–$26.07.
- **Margins by product** (`marketing_get_margin_by_product`):
  - Honey cake slice — $8.50, 68% margin
  - Whole honey cake — $55, 62% margin
  - Pistachio roll — $9.50, 64% margin
  - Custom birthday cake — $95, 58% margin
  - Office dessert box — $120, 60% margin
- **Google Business profile, last 30 days** (`gb_get_metrics`,
  `period:"last_30_days"`): 1,842 profile views · 1,340 search views ·
  502 map views · 87 directions requests · 41 call clicks · 96 website
  clicks. The map + directions + calls cluster (630 actions) is the
  load-bearing local-intent signal we lean on for the channel split.

## Budget allocation

| Channel | $ | Why this channel | Expected leads |
|---|---:|---|---:|
| google_local | 200 | Highest local intent in the data — 502 map views + 87 directions + 41 calls in 30d. Cheapest path to a same-day pickup. | ~200 |
| instagram | 150 | Visual product, weekend-ritual narrative, family / celebration moment. Reaches the 25–65 women audience inside Sugar Land / Houston metro. | ~163 |
| whatsapp | 150 | Direct neighbourhood conversation channel for birthday and anniversary asks; routes high-value or decoration requests to owner approval. | ~131 |
| **Total** | **500** | | **~494** |

**Math walkthrough.** Average ticket is $25.30 with 60–68% margins on the
ready-made line, so each incremental order contributes roughly $15–17 of
gross profit. To turn $500 into $5,000 of *revenue* we need ~200 incremental
orders — i.e. ~$2.50 per acquired order. That's only realistic on top of
the high-intent local-search cluster GMB already shows, which is why
google_local takes the largest single share. Instagram and WhatsApp split
the remainder — Instagram for reach into the family ritual moment, WhatsApp
for the warm seven-day birthday window where one or two messages convert
without paid distribution doing all the work.

## Campaign briefs

### 1. HappyCake — Honey cake from the neighbours

- **Channel:** google_local
- **Audience:** Women 25–65 with families in Sugar Land and the wider
  Houston metro (Anglo, Hispanic, Central + South Asian diaspora) already
  searching locally for cake, bakery, or honey cake. Primary 10-mile radius.
- **Offer:** Cake "Honey" by the slice or whole, ready today. The original
  taste of happiness, baked the way our grandmothers did.
- **Sample copy:**
  > Cake "Honey" — ready today.
  > The original taste of happiness, baked the way our grandmothers did.
  > Pickup in Sugar Land, ten minutes from where you're searching.
  > Order on the site at happycake.us or send a message on WhatsApp.

### 2. HappyCake — A weekend dessert for the table

- **Channel:** instagram
- **Audience:** Women 25–65 with families in Sugar Land and Houston metro
  (Anglo, Hispanic, Central + South Asian diaspora) who treat a Saturday
  dessert as a small family ritual and host weekend gatherings.
- **Offer:** A weekend dessert for the family table — cake "Pistachio Roll",
  cake "Honey", and cake "Napoleon", baked fresh and ready to pick up.
- **Sample copy:**
  > A weekend dessert for the family table.
  > Cake "Pistachio Roll", cake "Honey", cake "Napoleon".
  > Baked fresh, ready Friday and Saturday.
  > Order on the site at happycake.us or send a message on WhatsApp.

### 3. HappyCake — Birthdays this week

- **Channel:** whatsapp
- **Audience:** Women 25–65 with families in Sugar Land and Houston metro
  planning a birthday or anniversary inside the next seven days; existing
  neighbourhood customers and warm referrals.
- **Offer:** Cake "Honey", cake "Milk Maiden", or cake "Napoleon" baked
  fresh, with a small decoration if you'd like one. High-value or
  decoration-add-on requests escalate to owner approval.
- **Sample copy:**
  > A birthday this week?
  > Cake "Honey", cake "Milk Maiden", cake "Napoleon" — baked fresh.
  > A small decoration if you'd like one; otherwise the ready-made line.
  > Order on the site at happycake.us or send a message on WhatsApp.

## Simulated results

| Campaign | campaignId | Impressions | Clicks | Leads | Orders | Projected revenue |
|---|---|---:|---:|---:|---:|---:|
| Honey cake from the neighbours (google_local) | mkt_1778352184375 | 26,450 | 1,111 | 200 | 64 | $2,688 |
| A weekend dessert for the table (instagram) | mkt_1778352188704 | 21,563 | 906 | 163 | 52 | $2,184 |
| Birthdays this week (whatsapp) | mkt_1778352192686 | 17,250 | 725 | 131 | 42 | $1,764 |
| **Totals** | | **65,263** | **2,742** | **494** | **158** | **$6,636** |

ROAS at $500 spend → $6,636 projected revenue ≈ **13.27x**, ahead of the
10x challenge target.

## Lead routing

Nine leads routed (three per campaign):

| routeTo | Count |
|---|---:|
| owner_approval | 5 |
| website | 2 |
| whatsapp | 1 |
| instagram | 1 |

The routing rule was: high-value or decoration-bound asks (Maya's $95
custom birthday cakes and James's $120 office boxes) go straight to
`owner_approval` so Askhat confirms decoration brief and kitchen capacity
before commit. Standard same-day ready-made pickups (Nora's $55 honey
cake) stay in self-serve channels — `website` for the google_local /
instagram campaigns, and `whatsapp` when the lead arrived through the
WhatsApp birthdays campaign so the conversation stays in one place. One
Maya lead was routed to `instagram` instead of `owner_approval` so the
sales agent can collect the decoration brief in DMs first.

## Adjustments

| Campaign | What changed | Expected impact |
|---|---|---|
| mkt_1778352184375 (google_local) | Shift local search bid weighting toward mobile + within-5-mile-radius queries that include "honey cake", "bakery near me", or "cake today"; pause desktop placements outside 10 miles. GMB shows 502 map views + 87 direction requests in 30 days, so the high-intent local cluster is where the 5.76% click-to-order rate is actually coming from. | Lift order conversion from 5.76% toward 7% on the same $200, adding roughly 14 incremental orders (~$354 revenue) without raising spend. |
| mkt_1778352188704 (instagram) | Re-weight creative toward a Friday-evening and Saturday-morning posting window with cake "Pistachio Roll" and cake "Honey" as the hero shots on the family table. Demote single-slice still-life posts that don't show the ritual moment. | Hold CTR around 4.2% but raise lead-to-order from 31.9% to ~36% by tightening creative-to-intent fit, adding roughly 7 orders (~$294 revenue) inside the same $150. |
| mkt_1778352192686 (whatsapp) | Tighten WhatsApp outreach to existing neighbourhood customers and one-degree referrals with a confirmed birthday or anniversary in the next seven days; drop cold broadcast lists. Continue routing decoration or high-value asks to owner approval. | Trade some impressions for materially higher lead quality — expected lead-to-order lift from 32.1% to ~38% on the same $150, roughly 8 incremental orders (~$336 revenue) and fewer wasted owner pings. |

## Owner report

`marketing_report_to_owner` returned:

```json
{
  "budgetUsd": 500,
  "targetEffectUsd": 5000,
  "campaignsCreated": 3,
  "launches": 3,
  "leadsGenerated": 9,
  "leadsRouted": 9,
  "adjustments": 3,
  "projectedRevenueUsd": 6636,
  "ownerSummary": "Marketing simulator summary: 3 campaign(s), 9 lead(s), projected revenue $6636.",
  "reportedAt": "2026-05-09T18:44:30.860Z"
}
```

## If this were real next month

If we ran this for real next month I would (a) split the google_local
$200 into a tighter same-day pickup ad group ($120) and a separate
office-dessert-box B2B ad group ($80), since the bulk leads need owner
approval anyway and shouldn't compete for impressions with the ready-made
line; (b) move ~$30 from Instagram into a small WhatsApp broadcast list
of past birthday customers, because the warm seven-day window is the
single best-converting moment in the data; and (c) hold the cake "Honey"
and cake "Pistachio Roll" hero creative — the headline is the ready-made
line, not custom decoration. Worth flagging: re-running this script
creates duplicate sandbox campaigns each time — idempotency is
intentionally not enforced for the demo.

## Methodology note

This run called only the marketing-agent's allowed sandbox tools:
`marketing_get_budget`, `marketing_get_sales_history`,
`marketing_get_margin_by_product`, `square_recent_sales_csv`,
`gb_get_metrics`, `marketing_create_campaign`,
`marketing_launch_simulated_campaign`, `marketing_generate_leads`,
`marketing_route_lead`, `marketing_get_campaign_metrics`,
`marketing_adjust_campaign`, and `marketing_report_to_owner`. All
revenue, order, lead, and impression figures are simulator outputs, not
production numbers. The whole run is reproducible from
`agents/marketing/run.sh` plus a populated `.env.local` containing
`STEPPE_MCP_TOKEN`. Per-call evidence is appended to
`evidence/marketing.jsonl` by the wrapper.
