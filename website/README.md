# website/

The HappyCake US storefront — Next.js 15 App Router, TypeScript, Tailwind.
Designed to be **agent-readable**: machine endpoints at `/agent.json`,
`/api/catalog`, `/api/policies`, plus JSON-LD `Product` schema on every
product page.

## Local dev

```bash
cd website
npm install
npm run dev          # http://localhost:3000
```

The catalog is **snapshotted** at build time (or shipped as a fixture for
cold-start dev). Runtime MCP calls are limited to `/api/availability`, which
reads `square_get_inventory` and `kitchen_get_capacity` when
`STEPPE_MCP_TOKEN` is configured. Without that token it returns conservative
fallback copy so the storefront and agents do not promise stock or pickup
timing.

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

| Route | Purpose |
|---|---|
| `/` | Hero + featured cakes |
| `/menu` | Full catalog grouped by category |
| `/p/[slug]` | Product page with JSON-LD Product schema |
| `/about` | Brand story (from `docs/brand/HCU_BRANDBOOK.md`) |
| `/policies` | Pickup, delivery, allergens, returns |
| `/agent.json` | Well-known agent descriptor — capabilities, endpoints, hints |
| `/api/catalog` | Machine-readable catalog JSON |
| `/api/availability` | Machine-readable inventory + kitchen capacity, live via MCP when configured and conservative otherwise |
| `/api/policies` | Machine-readable policies JSON |

## Brand colors

From `docs/brand/HCU_BRANDBOOK.md` §4. Tailwind tokens in `tailwind.config.js`:

- `happy-blue-{900,700,500,200}` — primary blue scale
- `cream-{50,100,200}` — page background, cards, dot patterns
- `coral` — Mother's Day / love accent
- `leaf` — spring/Easter accent
- `ink` — body text on cream

Body font: Inter. Display font: Fraunces (serif, warm, traditional).

## Design notes

- **No images yet.** Placeholders use brand-blue gradients. Replace with the
  hackathon photo pack once we receive it (see `docs/HACKATHON_BRIEF.md` §7).
- **WhatsApp deeplink** is the universal CTA. Every product page sends a
  pre-filled message to the team's WA number. The brief explicitly says
  customers "buy by message" — we honor that, not fake checkout.
- **Refusals are baked in.** Brandbook §7 says HappyCake is not a custom-cake
  business. The /policies and /agent.json descriptors say so plainly so an
  agent crawler can refuse cleanly without inventing.
