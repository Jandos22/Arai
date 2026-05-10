import { findBySlug, loadCatalog, priceRange } from "./catalog";

export type OrderIntentInput = {
  productSlug?: string | null;
  variationId?: string | null;
  quantity?: number | null;
  customerName?: string | null;
  contact?: string | null;
  pickupDate?: string | null;
  pickupTime?: string | null;
  notes?: string | null;
  source?: "website" | "assistant";
  attribution?: CampaignAttributionInput | null;
};

export type CampaignAttributionInput = {
  landingPath?: string | null;
  campaign?: string | null;
  campaignId?: string | null;
  channel?: string | null;
  utm_source?: string | null;
  utm_medium?: string | null;
  utm_campaign?: string | null;
  utm_term?: string | null;
  utm_content?: string | null;
};

export type CampaignRoute = "website" | "whatsapp" | "instagram" | "owner_approval";

export type CampaignAttribution = {
  landingPath?: string;
  campaign?: string;
  campaignId?: string;
  channel?: string;
  utm: {
    source?: string;
    medium?: string;
    campaign?: string;
    term?: string;
    content?: string;
  };
  routeTo: CampaignRoute;
  evidence: string[];
};

export type OrderIntent = {
  intentId: string;
  source: "website" | "assistant";
  status: "captured_needs_confirmation" | "owner_review_required";
  attribution?: CampaignAttribution;
  product: {
    id: string;
    slug: string;
    name: string;
    variationId: string;
    variationName: string;
    unitPriceUsd: number;
    quantity: number;
    estimatedTotalUsd: number;
    leadTimeMinutes?: number;
    allergens?: string[];
  };
  customer: {
    name: string;
    contact: string;
    pickupDate?: string;
    pickupTime?: string;
    notes?: string;
  };
  handoff: {
    cashier: {
      tool: "square_create_order";
      source: "website" | "assistant";
      payloadPreview: Record<string, unknown>;
    };
    kitchen: {
      tool: "kitchen_create_ticket";
      when: "after cashier confirmation and capacity check";
      payloadPreview: Record<string, unknown>;
    };
    ownerGate: {
      required: boolean;
      reason?: string;
    };
    campaignLead?: {
      routeTo: CampaignRoute;
      evidence: string[];
    };
    availability: {
      endpoint: "/api/availability";
      requiredBeforePromise: true;
      inventoryTool: "square_get_inventory";
      capacityTool: "kitchen_get_capacity";
      fallbackRule: string;
    };
  };
  nextStep: string;
};

function safeText(value: string | null | undefined, fallback = ""): string {
  return (value ?? fallback).toString().trim().slice(0, 500);
}

function compactText(value: string | null | undefined): string | undefined {
  const text = safeText(value);
  return text || undefined;
}

function normalizeChannel(value: string | null | undefined): string | undefined {
  return compactText(value)?.toLowerCase().replace(/[^a-z0-9_-]/g, "_").slice(0, 40);
}

function routeCampaignLead(
  attribution: CampaignAttributionInput | null | undefined,
  ownerRequired: boolean,
): CampaignRoute {
  if (ownerRequired) return "owner_approval";
  const channel = normalizeChannel(attribution?.channel ?? attribution?.utm_source);
  if (channel === "whatsapp") return "whatsapp";
  if (channel === "instagram") return "instagram";
  return "website";
}

function campaignEvidence(
  attribution: CampaignAttributionInput,
  routeTo: CampaignRoute,
  ownerReason?: string,
): string[] {
  const campaign = compactText(attribution.campaign ?? attribution.utm_campaign) ?? "unlabeled campaign";
  const source = compactText(attribution.utm_source ?? attribution.channel) ?? "unknown source";
  const landingPath = compactText(attribution.landingPath) ?? "unknown landing path";
  const evidence = [
    `campaign=${campaign}`,
    `utm_source=${source}`,
    `landingPath=${landingPath}`,
    `routeTo=${routeTo}`,
  ];
  if (ownerReason) evidence.push(ownerReason);
  return evidence;
}

function normalizeAttribution(
  attribution: CampaignAttributionInput | null | undefined,
  ownerRequired: boolean,
  ownerReason?: string,
): CampaignAttribution | undefined {
  if (!attribution) return undefined;
  const routeTo = routeCampaignLead(attribution, ownerRequired);
  const normalized: CampaignAttribution = {
    landingPath: compactText(attribution.landingPath),
    campaign: compactText(attribution.campaign ?? attribution.utm_campaign),
    campaignId: compactText(attribution.campaignId),
    channel: normalizeChannel(attribution.channel ?? attribution.utm_source),
    utm: {
      source: compactText(attribution.utm_source),
      medium: compactText(attribution.utm_medium),
      campaign: compactText(attribution.utm_campaign),
      term: compactText(attribution.utm_term),
      content: compactText(attribution.utm_content),
    },
    routeTo,
    evidence: campaignEvidence(attribution, routeTo, ownerReason),
  };

  if (
    !normalized.landingPath &&
    !normalized.campaign &&
    !normalized.campaignId &&
    !normalized.channel &&
    Object.values(normalized.utm).every((value) => !value)
  ) {
    return undefined;
  }

  return normalized;
}

export function createOrderIntent(input: OrderIntentInput): OrderIntent {
  const catalog = loadCatalog();
  const item = input.productSlug ? findBySlug(input.productSlug) : catalog.items[0];
  if (!item) {
    throw new Error("No catalog item found for website order intent.");
  }

  const variation =
    item.variations.find((v) => v.id === input.variationId) ?? item.variations[0];
  const quantity = Math.max(1, Math.min(24, Number(input.quantity ?? 1) || 1));
  const total = Number((variation.priceUsd * quantity).toFixed(2));
  const notes = safeText(input.notes);
  const customSignals = /custom|design|theme|name|allerg|refund|complaint|problem|late|wrong/i.test(notes);
  const highValue = total > 80;
  const ownerRequired = customSignals || highValue;
  const ownerReason = ownerRequired
    ? highValue
      ? `Estimated total $${total} exceeds owner-gate threshold.`
      : "Customer notes include custom/allergy/complaint signal."
    : undefined;
  const attribution = normalizeAttribution(input.attribution, ownerRequired, ownerReason);
  const intentId = `web_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;

  return {
    intentId,
    source: input.source ?? "website",
    status: ownerRequired ? "owner_review_required" : "captured_needs_confirmation",
    attribution,
    product: {
      id: item.id,
      slug: item.slug,
      name: item.name,
      variationId: variation.id,
      variationName: variation.name,
      unitPriceUsd: variation.priceUsd,
      quantity,
      estimatedTotalUsd: total,
      leadTimeMinutes: item.leadTimeMinutes,
      allergens: item.allergens,
    },
    customer: {
      name: safeText(input.customerName, "Website customer"),
      contact: safeText(input.contact, "contact-needed"),
      pickupDate: safeText(input.pickupDate) || undefined,
      pickupTime: safeText(input.pickupTime) || undefined,
      notes: notes || undefined,
    },
    handoff: {
      cashier: {
        tool: "square_create_order",
        source: input.source ?? "website",
        payloadPreview: {
          items: [{ variationId: variation.id, quantity }],
          source: input.source ?? "website",
          attribution,
          customerName: safeText(input.customerName, "Website customer"),
          customerNote: notes || "Website order intent captured; confirm pickup before charging.",
        },
      },
      kitchen: {
        tool: "kitchen_create_ticket",
        when: "after cashier confirmation and capacity check",
        payloadPreview: {
          customerName: safeText(input.customerName, "Website customer"),
          items: [{ productId: item.kitchenProductId ?? item.id, quantity }],
          requestedPickupAt: [input.pickupDate, input.pickupTime].filter(Boolean).join("T") || undefined,
          notes: notes || "Website order intent captured; confirm pickup before prep.",
          attribution,
        },
      },
      availability: {
        endpoint: "/api/availability",
        requiredBeforePromise: true,
        inventoryTool: "square_get_inventory",
        capacityTool: "kitchen_get_capacity",
        fallbackRule:
          "If live availability is unavailable, do not promise stock or pickup timing; confirm with staff before accepting payment.",
      },
      ownerGate: {
        required: ownerRequired,
        reason: ownerReason,
      },
      campaignLead: attribution
        ? {
            routeTo: attribution.routeTo,
            evidence: attribution.evidence,
          }
        : undefined,
    },
    nextStep: ownerRequired
      ? "Owner review required before cashier/kitchen handoff. The Telegram owner gate receives this context in production."
      : "Confirm by WhatsApp/SMS, then create Square order and kitchen ticket if capacity allows.",
  };
}

export function orderSummaryForSlug(slug: string | undefined) {
  const item = slug ? findBySlug(slug) : undefined;
  if (!item) return null;
  const range = priceRange(item);
  return { item, range };
}
