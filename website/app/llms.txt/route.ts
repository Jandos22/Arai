import { loadCatalog } from "@/lib/catalog";

export const dynamic = "force-static";

const SITE_URL = "https://happycake.us";

export function GET() {
  const catalog = loadCatalog();
  const productLinks = catalog.items
    .map((item) => `- [${item.name}](${SITE_URL}/products/${item.slug}): ${item.description}`)
    .join("\n");

  const body = `# HappyCake US

Hand-baked traditional cakes in Sugar Land, Texas. Customers and agents can browse the catalog, read policies, check availability, and capture an order intent for pickup or local delivery.

## Agent Entry Points

- [Agent descriptor](${SITE_URL}/agent.json): Machine-readable capabilities, endpoints, policies, and order intent shape.
- [Agent guide](${SITE_URL}/agents): Human-readable guide for AI agents such as Hermes and OpenClaw-managed browser agents.
- [Catalog API](${SITE_URL}/api/catalog): Agent-readable product catalog.
- [Availability API](${SITE_URL}/api/availability): Inventory and kitchen capacity status. Do not promise stock or timing when the response says fallback or unavailable.
- [Policies API](${SITE_URL}/api/policies): Ordering, delivery, allergen, return, and owner-gate rules.
- [Order intent API](${SITE_URL}/api/order-intent): POST endpoint for structured pickup or delivery intent. Returns a mock provider-hosted payment link for non-owner-gated orders.
- [Payment intent API](${SITE_URL}/api/payment-intent): POST endpoint for a Square-style hosted-checkout mock. Arai never collects card data; production should use Square Checkout or Square Payment Links and signed webhooks.

## Primary Pages

- [Home](${SITE_URL}/)
- [Menu](${SITE_URL}/menu)
- [Order](${SITE_URL}/order)
- [Assistant](${SITE_URL}/assistant)
- [Policies](${SITE_URL}/policies)

## Products

${productLinks}
`;

  return new Response(body, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "public, max-age=600",
    },
  });
}
