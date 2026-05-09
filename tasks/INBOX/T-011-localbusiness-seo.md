# T-011 — LocalBusiness JSON-LD + Open Graph + sitemap

**Owner:** Hermes
**Dependencies:** T-002 done
**Estimated:** 15 min
**Bonus bucket:** Growth upside (+5 — local SEO) + Production readiness (+5 — clean deploy / SEO discoverability)

## Why

The hackathon brief explicitly grades **agent-readable + production-ready** websites. We have JSON-LD `Product` schema on every product page already. Missing: site-level **`LocalBusiness`** schema (Sugar Land address, hours, phone, geo) and **Open Graph** tags so the site previews well when shared on WhatsApp, IG, Telegram. Plus a `sitemap.xml` so an evaluator AI agent can crawl the catalog.

Three small additions, all in `website/app/`:

## Tasks

1. **Site-level `LocalBusiness` JSON-LD** in `app/layout.tsx`
   - `@type`: `Bakery` (extends LocalBusiness)
   - `name`: `HappyCake US`
   - `address`: Sugar Land, TX placeholder (use `2123 Hwy 6 South, Sugar Land, TX 77478` as placeholder — note as placeholder in source comment, real address is per Askhat)
   - `telephone`: `+1-281-555-1234` placeholder
   - `openingHoursSpecification`: Tue–Sat 10:00–19:00, Sun 11:00–17:00, closed Mon (placeholder)
   - `priceRange`: `$$`
   - `servesCuisine`: `Desserts, Cakes`
   - `image`: `/brand/hero/hero-04.webp`

2. **Open Graph + Twitter Card metadata** in `app/layout.tsx` `metadata` export
   - `openGraph.images` → hero photo
   - `openGraph.locale` → `en_US`
   - `twitter.card` → `summary_large_image`
   - Per-page `metadata.openGraph` overrides for product pages (use product image)

3. **`app/sitemap.ts`** (Next.js 15 idiom)
   - Static: `/`, `/menu`, `/about`, `/policies`
   - Dynamic: every `/p/<slug>` from `loadCatalog()`
   - `lastModified`: `catalog.capturedAt`

4. **`app/robots.ts`** — allow all, point to sitemap

## Acceptance

- `curl localhost:3000/sitemap.xml` returns valid XML with all routes
- `curl localhost:3000/` shows `<script type="application/ld+json">` containing `"@type":"Bakery"`
- `curl localhost:3000/` shows `<meta property="og:image"`
- Build still clean (`npm run build` exits 0)

## Out of scope

- Real address/phone/hours (placeholder is fine; document in source as TODO for Askhat)
- Multi-language hreflang (English-only is the spec)
