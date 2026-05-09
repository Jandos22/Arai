# Agent-friendly website — design notes

> The brief (§3, "Agent-friendly website") explicitly asks for a site that an
> *autonomous customer-side AI agent* can read without brittle scraping. This
> doc explains how `website/` is built to satisfy that requirement.

## What "agent-friendly" means here

A customer-side agent (think: someone's personal AI assistant tasked with
"order me a birthday cake from a Sugar Land bakery") should be able to:

1. **Discover** the site's capabilities and constraints without crawling HTML.
2. **Read** product data, prices, and policies from a stable JSON contract.
3. **Decide** whether HappyCake meets the user's need (custom cake? same-day
   pickup? gluten-free?).
4. **Act** — drop into a confirmable order channel (WhatsApp deeplink) with
   the right context pre-filled.
5. **Refuse cleanly** when HappyCake doesn't sell what was asked (custom
   sculpted cake, dietary specials we can't promise) — without inventing.

The website provides four contracts to make all five steps mechanical.

## Contract #1 — `/agent.json` (well-known descriptor)

`GET https://happycake.us/agent.json` → JSON descriptor. Inspired by
`/.well-known/ai-plugin.json` conventions but slimmer.

Shape (see `website/app/agent.json/route.ts` for the live source):

```json
{
  "schemaVersion": "v1",
  "name": "HappyCake US",
  "shortDescription": "Hand-baked traditional cakes in Sugar Land, TX. The original taste of happiness.",
  "longDescription": "...",
  "contact": { "whatsapp": "...", "instagram": "...", "email": "..." },
  "endpoints": {
    "catalog": "/api/catalog",
    "policies": "/api/policies",
    "productPage": "/p/{slug}",
    "menu": "/menu"
  },
  "capabilities": ["browse_catalog", "read_policies", "deeplink_whatsapp_order", "deeplink_instagram_dm"],
  "notSupported": ["online_payment_on_site", "real_time_order_status_via_website", "custom_decoration_requests_outside_owner_review"],
  "hints": {
    "preferredOrderChannels": ["whatsapp", "instagram"],
    "confirmationFlow": "...",
    "leadTimeMinutesDefault": 90,
    "leadTimeMinutesCustomName": 180
  },
  "policiesSummary": { "customCakes": false, "decoration": "...", "delivery": {...}, "allergens": [...], "returns": "..." },
  "brand": { "voice": "...", "refusalStyle": "..." }
}
```

The `notSupported` array is the load-bearing field for refusals. A
customer-side agent that reads this knows immediately not to invent a
"custom unicorn-shaped cake" path.

## Contract #2 — `/api/catalog` (machine-readable products)

`GET /api/catalog` → JSON array of products with stable IDs, slugs,
variations, prices, lead times, allergens. Source-of-truth is the sandbox
MCP `square_list_catalog` tool, snapshotted at build time by
`website/scripts/snapshot-catalog.ts`. A `_orderPath` field tells the agent
how to convert intent into action (WhatsApp deeplink with pre-filled
message).

Cache header: `public, max-age=300` — agents can poll cheaply.

## Contract #3 — `/api/policies` (operational rules)

`GET /api/policies` → structured JSON of:

- Business identity (name, location, contact channels)
- Ordering channels + confirmation flow + lead times + delivery area + fee
- Product policy (`customCakes: false`, decoration rules, consistency-over-variety stance)
- Allergens (common, sometimes, cross-contact disclaimer)
- Returns / make-good policy
- Voice + refusal style
- An `agentNotes` block with the suggested confirmation flow + escalation triggers

This is the contract that makes refusals possible: when the policy says
`customCakes: false`, an agent doesn't even need to ask the LLM — it can
short-circuit and route the user to a different bakery, or pick the
closest catalog item.

## Contract #4 — JSON-LD `Product` schema on every product page

Every `/p/<slug>` page emits `<script type="application/ld+json">` with the
canonical `schema.org/Product` shape:

```json
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Medovik — Honey Cake",
  "description": "...",
  "brand": { "@type": "Brand", "name": "HappyCake US" },
  "category": "signature",
  "offers": [
    { "@type": "Offer", "sku": "...", "name": "Small (serves 6)", "price": 36, "priceCurrency": "USD", "availability": "https://schema.org/InStock", "seller": {...} },
    { "@type": "Offer", "sku": "...", "name": "Medium (serves 10)", "price": 58, "priceCurrency": "USD", "availability": "https://schema.org/InStock", "seller": {...} }
  ],
  "additionalProperty": [
    { "@type": "PropertyValue", "name": "leadTimeMinutes", "value": 90 },
    { "@type": "PropertyValue", "name": "allergens", "value": "wheat, egg, dairy" }
  ]
}
```

Agents that prefer schema.org over our custom JSON can use this; both
contracts agree. Verified by `scripts/test_website.sh`.

## Contract verification

`scripts/test_website.sh` runs against a fresh `npm run build` + `npm start`
and asserts:

- `/agent.json` returns a non-empty `name` + `capabilities`
- `/api/catalog` returns ≥1 item, each with `id`/`slug`/`name`/`variations`
- `/api/policies` returns the canonical business + ordering shape
- Every product page contains `application/ld+json`
- All static pages return HTTP 200

Exit code is the contract: 0 means an autonomous agent will not be
surprised; non-zero means we shipped a regression.

## How the orchestrator uses these contracts

The orchestrator's sales agent (`agents/sales/`, T-005) is told to **prefer
catalog reads via the MCP** but **fall back to `/api/catalog`** when MCP is
slow or partially down. This is by design: the website endpoints are a
deterministic, cached mirror of the MCP catalog. Same contract, two
delivery mechanisms, redundancy for free.

## Brand-voice alignment

The agent-friendly contracts live alongside the human-readable site, but
they agree on voice:

- Marketing copy on `/`, `/menu`, `/about` reflects brandbook §1+§2: warm,
  unstaged, traditional, Sugar Land family-focused.
- `/agent.json#brand.voice` and `/api/policies#voice` carry the same tone
  description. An LLM agent reading either will compose replies in
  HappyCake voice without us having to ship a separate prompt.
- `notSupported` enforces brandbook §1's "we are not a custom-cake
  business" stance machine-readably.

## What we'd add given more time

- `Idempotency-Key` header on the `/api/catalog` deeplink encoding (right
  now the WhatsApp link is a plain URL — works fine, but a structured
  intent blob would let agents handshake order context without a prose
  message).
- A `webhook` capability advertising `/api/agent-callback` so customer-side
  agents could subscribe to inventory changes (out of hackathon scope).
- robots.txt + `llms.txt` — useful for discoverability, deferred until
  post-hackathon real deployment.

## TL;DR for judges

Three URLs prove the agent-friendly story end-to-end:

```
GET /agent.json     # what we sell, what we don't, how to buy
GET /api/catalog    # current products, prices, lead times
GET /api/policies   # delivery, allergens, refunds, voice
```

Plus JSON-LD on every `/p/<slug>` page. Verified by
`scripts/test_website.sh`. Mirrors the sandbox MCP catalog so agents can
choose either delivery path.
