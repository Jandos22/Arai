# T-002: Website skeleton + agent-readable storefront

**Owner:** Hermes (Mac mini)
**Branch:** `feat/website`
**Estimated:** 90 min
**Depends on:** T-001 (have `docs/MCP-TOOLS.md` to know catalog tool shape)

## Goal
Stand up `website/` as a Next.js app that *is* the agent-readable Happy Cake storefront. The catalog comes from `square_list_catalog` at build time (or via a thin proxy). JSON-LD on every product page. Policies and constraints exposed as machine-readable JSON endpoints. Pretty UI is a bonus, agent-readability is mandatory.

## Acceptance
- [ ] `website/` next.js app boots with `npm run dev`
- [ ] `/` lists products, names + photos + prices from a catalog JSON cached from MCP
- [ ] `/p/[slug]` product page with JSON-LD `Product` schema + buy-intent CTA → WhatsApp deeplink
- [ ] `/api/catalog` returns the same catalog as plain JSON (agent-friendly)
- [ ] `/api/policies` returns lead times, custom-cake rules, pickup/delivery, allergens (sourced from brandbook + `kitchen_get_menu_constraints`)
- [ ] `/agent.json` (or well-known) describes site capabilities for an agent crawler — endpoints, schema
- [ ] Brand colors + voice from `docs/brand/HCU_BRANDBOOK.md`
- [ ] Repo includes `website/scripts/snapshot-catalog.ts` that calls `square_list_catalog` against the live MCP and writes `website/data/catalog.json` (skipped if no token; uses fixture as fallback)
- [ ] README.md updated with website quickstart

## Out of scope
- On-site assistant chat widget (separate task later if time permits)
- Real Stripe/Square checkout (sandbox only — CTA goes to WA deeplink)
- SEO polish / production deploy (we'll Vercel-deploy at the end if time)

## Notes
- Use App Router, TypeScript, Tailwind. Keep it minimal — no shadcn install, hand-rolled is fine.
- Catalog snapshot script must work from `.env.local`; never bake the token into builds.
