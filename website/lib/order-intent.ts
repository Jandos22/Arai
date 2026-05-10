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
};

export type OrderIntent = {
  intentId: string;
  source: "website" | "assistant";
  status: "captured_needs_confirmation" | "owner_review_required";
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
  };
  nextStep: string;
};

function safeText(value: string | null | undefined, fallback = ""): string {
  return (value ?? fallback).toString().trim().slice(0, 500);
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
  const intentId = `web_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;

  return {
    intentId,
    source: input.source ?? "website",
    status: ownerRequired ? "owner_review_required" : "captured_needs_confirmation",
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
          source: input.source ?? "website",
          variationId: variation.id,
          quantity,
          customerName: safeText(input.customerName, "Website customer"),
          customerNote: notes || "Website order intent captured; confirm pickup before charging.",
        },
      },
      kitchen: {
        tool: "kitchen_create_ticket",
        when: "after cashier confirmation and capacity check",
        payloadPreview: {
          productId: item.id,
          quantity,
          requestedPickup: [input.pickupDate, input.pickupTime].filter(Boolean).join(" ") || "TBD",
        },
      },
      ownerGate: {
        required: ownerRequired,
        reason: ownerRequired
          ? highValue
            ? `Estimated total $${total} exceeds owner-gate threshold.`
            : "Customer notes include custom/allergy/complaint signal."
          : undefined,
      },
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
