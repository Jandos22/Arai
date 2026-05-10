# website/

The HappyCake US storefront: Next.js 15 App Router, TypeScript, Tailwind,
agent-readable APIs, availability-aware storefront copy, and a website
order-intent path for cashier/kitchen handoff demos.

The site is designed for both humans and agents:

- Human storefront pages expose the catalog, policies, product detail pages,
  order form, and on-site assistant.
- Machine endpoints expose `/agent.json`, catalog/policy/availability JSON,
  assistant triage, and order-intent payloads.
- Every product page includes JSON-LD `Product` schema.

## Local dev

```bash
cd website
npm install
npm run dev          # http://localhost:3000
```

The catalog is **snapshotted** at build time or loaded from the fixture for
cold-start dev. Runtime MCP calls are limited to `/api/availability`, which
reads `square_get_inventory` and `kitchen_get_capacity` when
`STEPPE_MCP_TOKEN` is configured. Without that token it returns conservative
fallback copy so the storefront and agents do not promise stock or pickup
timing.

## Build and production run

```bash
cd website
npm install
npm run build
npm run start        # serves the production build
```

Static pages and route handlers are safe to deploy on a standard Next.js host
such as Vercel, Netlify, or a Node server. The current Next config keeps image
optimization disabled (`images.unoptimized = true`) because the curated brand
assets are already committed as web-ready files under `public/brand`.

Production order handling still requires a backend adapter before charging
customers or creating kitchen tickets. The website captures structured intent;
the production adapter should confirm customer contact, check capacity, create
the Square order, and then create the kitchen ticket. See
[`../docs/PRODUCTION-PATH.md`](../docs/PRODUCTION-PATH.md) for the real API
adapter and credential rollout path.

## Catalog snapshot from sandbox

```bash
# from the website/ folder, with repo .env.local or ~/.config/arai/env.local populated
source ../scripts/load_env.sh && arai_load_env ..
npm run snapshot:catalog
```

This runs `scripts/snapshot-catalog.ts`, calls `square_list_catalog` against
the team's MCP, and writes `data/catalog.json`. The fixture
`data/catalog.fixture.json` stays in repo for offline development. The
generated `data/catalog.json` is **gitignored** to avoid stale snapshots in
git history.

## Routes

### Human pages

| Route | Purpose |
|---|---|
| `/` | Storefront home with hero imagery, featured cakes, availability copy, and order CTAs |
| `/menu` | Full catalog grouped by category with prices and lead times |
| `/p/[slug]` | Product page with JSON-LD Product schema |
| `/about` | Brand story (from `docs/brand/HCU_BRANDBOOK.md`) |
| `/policies` | Pickup, delivery, allergens, returns |
| `/order` | Website order-intent form; accepts optional `?product=<slug>` |
| `/assistant` | On-site assistant UI for catalog, policy, custom, complaint, status, and order-intent triage |
| `/office-boxes` | Campaign landing page for attributed Sugar Land office dessert-box orders |

### Agent-readable endpoints

| Route | Purpose |
|---|---|
| `/agent.json` | Well-known agent descriptor with capabilities, endpoints, unsupported actions, owner-gate hints, and policy summary |
| `/api/catalog` | Machine-readable catalog JSON plus ordering-channel notes |
| `/api/availability` | Machine-readable inventory + kitchen capacity, live via MCP when configured and conservative otherwise |
| `/api/policies` | Machine-readable business, ordering, allergen, return, voice, and agent-flow policies |
| `/api/order-intent` | `POST` endpoint that captures structured website order intent |
| `/api/assistant` | `POST` endpoint that classifies assistant messages and returns answer, escalation, and handoff metadata |

`/agent.json` is the top-level contract for crawlers and agent clients. It links
the catalog, availability, policy, assistant, order-intent, product, menu,
order, and assistant-page surfaces in one descriptor.

## Order-intent contract

`POST /api/order-intent` accepts:

```json
{
  "productSlug": "honey-cake",
  "variationId": "optional-catalog-variation-id",
  "quantity": 1,
  "customerName": "Customer name",
  "contact": "+1 ...",
  "pickupDate": "2026-05-09",
  "pickupTime": "14:30",
  "notes": "Occasion, allergies, name-on-cake, or complaint context"
}
```

The endpoint returns `201` with:

- `ok: true`
- `intent.status`: `captured_needs_confirmation` or `owner_review_required`
- `intent.product`: selected item, variation, quantity, estimated total, lead
  time, and allergens
- `intent.customer`: captured contact and pickup details
- `intent.handoff`: `square_create_order`, `kitchen_create_ticket`, and
  owner-gate preview metadata
- `intent.nextStep`: cashier/kitchen confirmation guidance

Owner review is required when notes include custom/design/name/allergy,
complaint/problem/late/wrong signals, or when the estimated total is above the
owner-gate threshold.

## Assistant contract

`POST /api/assistant` accepts:

```json
{
  "message": "Which cake works for 10 people today?",
  "productSlug": "optional-product-slug",
  "customerName": "optional",
  "contact": "optional"
}
```

The endpoint classifies messages into:

- `catalog`
- `custom_order`
- `complaint`
- `status`
- `policy`
- `order_intent`

Responses include `ok`, `intent`, `answer`, and, when relevant,
`escalation`, `suggestedActions`, `endpoints`, or `orderIntent`. The
`order_intent` path calls the same `createOrderIntent` helper as
`/api/order-intent`, with `source: "assistant"`.

## Brand colors

From `docs/brand/HCU_BRANDBOOK.md` section 4. Tailwind tokens in
`tailwind.config.js`:

- `happy-blue-{900,700,500,200}` - primary blue scale
- `cream-{50,100,200}` - page background, cards, dot patterns
- `coral` - Mother's Day / love accent
- `leaf` - spring/Easter accent
- `ink` - body text on cream

Body font: Inter. Display font: Fraunces (serif, warm, traditional).

## Asset usage

Approved, web-ready assets live under `public/brand`:

- `logo/` contains optimized PNG logo sizes.
- `hero/` contains storefront hero WebP images.
- `products/` contains square product WebP images.
- `social/` contains social crop WebP images used by the site and marketing
  previews.
- `metadata.json` documents the private source inventory and curation rules.

Raw originals and private source paths must not be copied into public assets or
rendered by the website. Use only the curated `public/brand` files unless the
launch gate and brand owner approve a new export.

## Implementation notes

- **Website order intent, not checkout.** `/order` and `/api/order-intent`
  capture structured intent for cashier/kitchen handoff. They do not charge
  cards or promise production fulfillment.
- **Assistant is deterministic triage.** `/assistant` and `/api/assistant`
  cover catalog guidance, policies, custom-order routing, complaints, status
  questions, and order-intent capture with owner-gate metadata.
- **Availability is conservative by default.** `/api/availability` can read
  sandbox MCP inventory/capacity when configured, but its fallback path avoids
  promising stock or pickup timing.
- **WhatsApp remains a core CTA.** Product pages still deep-link to WhatsApp
  because the business confirms orders by message before kitchen work starts.
- **Refusals are baked in.** Brandbook section 7 says HappyCake is not a
  custom-cake business. The `/policies` and `/agent.json` descriptors say so
  plainly so an agent crawler can refuse cleanly without inventing.
- **CORS headers are read-oriented.** `next.config.js` allows `GET` and
  `OPTIONS` for `/api/:path*` to support agent readers. POST callers for
  assistant/order-intent should run from the site origin or through the
  production adapter.
