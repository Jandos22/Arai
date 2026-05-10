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
    whatsapp: "https://wa.me/12819798320",
    instagram: "https://instagram.com/happycakeus",
    email: "hello@happycake.us",
  },
  endpoints: {
    catalog: "/api/catalog",
    availability: "/api/availability",
    policies: "/api/policies",
    assistant: "/api/assistant",
    orderIntent: "/api/order-intent",
    productPage: "/products/{slug}",
    menu: "/menu",
    orderPage: "/order?product={slug}",
    assistantPage: "/assistant",
  },
  capabilities: [
    "browse_catalog",
    "read_policies",
    "read_live_inventory_and_capacity_when_configured",
    "capture_website_order_intent",
    "onsite_assistant_product_guidance",
    "onsite_assistant_custom_order_triage",
    "onsite_assistant_complaint_triage",
    "onsite_assistant_order_status_triage",
    "owner_gate_escalation_metadata",
    "deeplink_whatsapp_order",
    "deeplink_instagram_dm",
  ],
  notSupported: [
    "online_payment_on_site",
    "website_direct_charge_without_cashier_confirmation",
    "custom_decoration_requests_outside_owner_review",
  ],
  hints: {
    preferredOrderChannels: ["website_order_intent", "whatsapp", "instagram"],
    confirmationFlow:
      "Website /api/order-intent captures a structured source=website intent. /api/availability exposes Square inventory and kitchen capacity when MCP is configured. Production adapter confirms customer contact, then calls Square and kitchen capacity-aware handoff. Custom, allergy, complaint, and high-value cases include owner-gate metadata for Telegram approval.",
    availabilityRule:
      "If /api/availability source is conservative-fallback or a tool state is not live, do not promise stock or same-day pickup. Ask for a pickup window and wait for confirmation.",
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
