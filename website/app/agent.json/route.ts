// Serve /agent.json at the well-known root path via a static rewrite-equivalent
// route. We use a `route.ts` at app/agent.json/route.ts — Next will resolve it.

export const dynamic = "force-static";

const descriptor = {
  schemaVersion: "v1",
  name: "HappyCake US",
  shortDescription:
    "Hand-baked traditional cakes in Sugar Land, TX. The original taste of happiness.",
  longDescription:
    "HappyCake US is a Sugar Land, Texas bakery selling hand-decorated traditional cakes — Medovik (honey), Napoleon, red velvet, chocolate truffle, vanilla birthday, carrot & walnut. We are not a custom-cake business; consistency is the value proposition. Order ahead by WhatsApp, Instagram, or this website; pick up at our kitchen or arrange local delivery.",
  contact: {
    whatsapp: "https://wa.me/12815551234",
    instagram: "https://instagram.com/happycakeus",
    email: "hello@happycake.us",
  },
  endpoints: {
    catalog: "/api/catalog",
    policies: "/api/policies",
    productPage: "/p/{slug}",
    menu: "/menu",
  },
  capabilities: [
    "browse_catalog",
    "read_policies",
    "deeplink_whatsapp_order",
    "deeplink_instagram_dm",
  ],
  notSupported: [
    "online_payment_on_site",
    "real_time_order_status_via_website",
    "custom_decoration_requests_outside_owner_review",
  ],
  hints: {
    preferredOrderChannels: ["whatsapp", "instagram"],
    confirmationFlow:
      "After customer expresses intent on WhatsApp or Instagram, the HappyCake sales agent confirms cake, size, pickup, date/time, and any allergy concern before the kitchen starts.",
    leadTimeMinutesDefault: 90,
    leadTimeMinutesCustomName: 180,
  },
  policiesSummary: {
    customCakes: false,
    decoration: "hand-piped name only, case-by-case",
    delivery: { area: "Sugar Land + Houston metro", feeUsd: { min: 8, max: 15 } },
    allergens: ["wheat", "egg", "dairy", "tree-nut (some)", "soy (some)"],
    returns:
      "Same-day photo + WhatsApp message; we replace cakes that don't meet the bar.",
  },
  brand: {
    voice: "Warm, confident, unstaged. Resolves, never abandons. Always ends with a next step.",
    refusalStyle:
      "Polite — when something we don't sell is asked for (custom sculpted cakes, exotic flavours), point to the closest item on our menu.",
  },
  jurisdiction: { country: "US", region: "TX", city: "Sugar Land" },
};

export function GET() {
  return Response.json(descriptor, {
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "public, max-age=600",
    },
  });
}
