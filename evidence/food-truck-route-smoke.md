# Food-truck weekly route — smoke evidence

Bonus marketing capability for HappyCake. The marketing agent clusters
customer addresses geographically, proposes a Mon–Fri food-truck route
(one neighbourhood cluster per weekday, 3:00 PM – 7:00 PM window),
drafts an Instagram post per stop and a personalised WhatsApp message
per customer, and projects the incremental orders + revenue per month
that come from the frequency-and-geography lift.

The unit-economics story: HappyCake operates one Sugar Land storefront,
so most customers cap at ~1 order / month because the drive is too far
to repeat. A weekly truck stop within ~5 miles of a customer's home
removes that friction; we model the lift at ×1.85 (a deliberately
modest multiplier — the demo's value is the geography-clustering and
brand-voice content, not the choice of constant).

## Reproduce

```
python scripts/food_truck_route.py \
  --stem food-truck-route-sample \
  --at 2026-05-10T08:00:00Z
```

The driver is deterministic given `--seed` (default 7) and the fixture
at `orchestrator/fixtures/food_truck_customers.json` (25 customers
across First Colony / Telfair / Sienna / Stafford / Aliana / Pearland).

Outputs:

- `evidence/food-truck-route-sample.json` — agent-readable artifact
- `evidence/food-truck-route-sample.md` — owner-readable summary

## Headline numbers (sample run)

| Metric | Value |
|---|---:|
| Stops in week | 5 |
| Customers covered | 25 |
| Baseline orders / month (single-store today) | 23.2 |
| Projected orders / month with truck | 42.93 |
| **Incremental orders / month** | **+19.73** |
| **Incremental revenue / month** | **+$892.25** |

The five stops the planner chose for this fixture:

| Day | Anchor | Customers | Hero | Δ orders/mo | Δ revenue/mo |
|---|---|---:|---|---:|---:|
| Mon | Telfair | 9 | cake "Honey" | 7.40 | $278.20 |
| Tue | Silverlake | 5 | cake "Honey" | 2.89 | $119.09 |
| Wed | Stafford | 5 | cake "Napoleon" | 4.50 | $283.05 |
| Thu | Sienna | 4 | cake "Honey" | 3.32 | $140.08 |
| Fri | Aliana | 2 | cake "Milk Maiden" | 1.62 | $71.83 |

## Evidence shape (matches existing JSONL convention)

```jsonl
{"kind":"marketing.food_truck_weekly_route","agent":"marketing","generatedAt":"2026-05-10T08:00:00Z","evidenceSources":["customer_fixture","deterministic_kmeans"],"summary":{"stops":5,"customers":25,"baselineOrdersMonth":23.2,"projectedOrdersMonth":42.93,"incrementalOrdersMonth":19.73,"incrementalRevenueMonthUsd":892.25,"liftFactor":1.85,"nearRadiusMiles":5.0}}
```

Per-stop record (one of five) with embedded IG post + per-customer
WhatsApp drafts + projection breakdown:

```jsonl
{"weekday":"Mon","window":"3:00 PM – 7:00 PM","cluster":{"label":"A","anchorNeighborhood":"Telfair","centroid":{"lat":29.581,"lng":-95.6422},"customerCount":9,"customerIds":["+12815550111","+12815550112","+12815550113","@diana_cake","+12815550115","@farah_eats","+12815550141","+12815550142","+12815550145"]},"heroSku":"honey-whole","heroCopy":"cake \"Honey\"","projection":{"baselineOrdersMonth":8.7,"projectedOrdersMonth":16.1,"incrementalOrdersMonth":7.4,"incrementalRevenueMonthUsd":278.2,"liftFactor":1.85,"nearRadiusMiles":5.0}}
```

## Brand-voice rules verified by tests

`orchestrator/tests/test_food_truck_route.py` asserts that every
generated post and every per-customer template:

- uses the **HappyCake** wordmark (one word, never "Happy Cake")
- references the cake by `cake "Name"` form (straight quotes after the
  word *cake*) for every catalog SKU
- includes the slogan *the original taste of happiness* in IG copy
- closes with the standard CTA tail: *Order on the site at happycake.us
  or send a message on WhatsApp.*
- contains no emoji and none of the banned superlatives (*amazing*,
  *awesome*, *incredible*, *unbelievable*, exclamation chains)

## How this slots into the existing system

The agent runtime is unchanged: the marketing agent already lives at
`agents/marketing/`. This module is a deterministic capability the
agent can invoke through `Read`/`Bash` (the same tools it already
uses), or via the standalone driver above for reproducible artifacts.
The owner-approval flow is the same as elsewhere in the repo —
Telegram inline buttons; the artifact's JSON is the payload, the
Markdown is the human-readable summary the bot links to.

No real food-truck logistics, no real geocoding API call, no real send
to Instagram or WhatsApp — every draft sits in `evidence/` for review
and would be queued into the existing channel handlers on owner
approval.

## Ownership flags

- New module: `orchestrator/food_truck_route.py`
- New tests: `orchestrator/tests/test_food_truck_route.py` (14 cases)
- New fixture: `orchestrator/fixtures/food_truck_customers.json`
- New driver: `scripts/food_truck_route.py`
- Touches `docs/MARKETING.md` (Hermes-owned `docs/`) — flagged in commit.
