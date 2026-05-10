export const dynamic = "force-static";

const policies = {
  business: {
    name: "HappyCake US",
    location: "Sugar Land, TX (Houston metro)",
    contact: {
      whatsapp: "+1-281-979-8320",
      whatsappDeepLink: "https://wa.me/12819798320",
      instagram: "https://instagram.com/happycakeus",
      email: "hello@happycake.us",
    },
    hours: { mon_fri: "10:00–19:00 CT", sat: "10:00–18:00 CT", sun: "10:00–16:00 CT" },
  },
  ordering: {
    channels: ["walk-in", "whatsapp", "instagram", "website"],
    confirmation:
      "Owner or sales agent confirms by message before kitchen starts the cake. Stock and pickup timing must be checked against /api/availability first.",
    minimumLeadTimeMinutes: 90,
    customNameLeadTimeMinutes: 180,
    availabilityEndpoint: "/api/availability",
    promiseRule:
      "Lead times are planning estimates. If /api/availability is in conservative fallback or live tools are unavailable, do not promise same-day pickup or in-stock status.",
    pickupAddress: "TBD — confirm at order",
    deliveryArea: "Sugar Land + nearby Houston metro",
    deliveryFeeUsd: { min: 8, max: 15 },
  },
  product: {
    customCakes: false,
    decorationPolicy:
      "Decoration beyond a hand-piped name is case-by-case, only when the kitchen has time. We do not promise themed or sculpted decoration.",
    consistencyOverVariety: true,
  },
  allergens: {
    common: ["wheat", "egg", "dairy"],
    sometimes: ["tree-nut", "soy"],
    crossContact:
      "Shared kitchen — cannot guarantee zero cross-contact. Tell us about a serious allergy and we will be honest about what we can promise.",
  },
  returns: {
    policy:
      "If a cake doesn't meet the bar, send a photo on WhatsApp same-day. We replace it. We don't delete reviews and we don't argue with people who weren't happy.",
  },
  voice: {
    tone: "Warm, confident, unstaged. We resolve, we don't abandon. Every reply ends with a clear next step.",
    refusal:
      "We refuse politely when something we don't sell is asked for (custom sculpted cakes, exotic flavours of the week). We point to the closest cake on our menu.",
  },
  agentNotes: {
    sourceOfTruth: "square_list_catalog (sandbox MCP)",
    suggestedFlow:
      "When a customer expresses intent, ask for: cake choice, size, pickup or delivery, date/time, hand-piped name (if any), allergy notes. Confirm against /api/catalog, /api/availability, and /api/policies. Hand off to owner via Telegram for any custom-decoration request, allergy promise, order > $80, or unavailable live capacity.",
  },
};

export function GET() {
  return Response.json(policies, { headers: { "Cache-Control": "public, max-age=600" } });
}
