// Deterministic upsell suggestion. One add-on per order intent — never two.
// Rule of taste: pair celebration-line with a candle/topper note, signature
// whole cake with a slice "to try", and large/office orders with a delivery
// reminder. Returns null when no clean pairing applies — silence is fine.

import type { CatalogItem } from "./catalog";

export type UpsellSuggestion = {
  kind: "complementary_sku" | "candle_addon" | "delivery_note";
  sku?: string;
  name: string;
  priceUsd?: number;
  message: string;
  reason: string;
};

const CELEBRATION_SLUGS = new Set([
  "red-velvet",
  "chocolate-truffle",
  "custom-birthday-cake",
]);

const SIGNATURE_SLUGS = new Set(["medovik-honey-cake", "napoleon"]);

// Whole-cake pair candidates for the signature-cake upsell. Pick the first
// available match that is NOT the same SKU the customer is buying.
const SIGNATURE_PAIR_SLUGS = ["pistachio-roll", "napoleon", "milk-maiden"];

function cheapestVariation(item: CatalogItem) {
  return [...item.variations].sort((a, b) => a.priceUsd - b.priceUsd)[0];
}

export function suggestUpsell(
  item: CatalogItem,
  catalogItems: CatalogItem[],
  totalUsd: number,
): UpsellSuggestion | null {
  if (!item) return null;

  if (CELEBRATION_SLUGS.has(item.slug)) {
    return {
      kind: "candle_addon",
      name: "Birthday candle set",
      priceUsd: 4,
      message:
        `Want me to add a candle set ($4) and pipe a name on the cake "${item.name}" — neighbour-table standard.`,
      reason: "celebration line, low-friction add-on",
    };
  }

  if (SIGNATURE_SLUGS.has(item.slug)) {
    const pair = SIGNATURE_PAIR_SLUGS
      .filter((slug) => slug !== item.slug)
      .map((slug) => catalogItems.find((i) => i.slug === slug))
      .find((found): found is CatalogItem => Boolean(found));
    if (pair) {
      const v = cheapestVariation(pair);
      return {
        kind: "complementary_sku",
        sku: v?.id,
        name: pair.name,
        priceUsd: v?.priceUsd,
        message:
          `Quick add — neighbours often pair this with cake "${pair.name}" (from $${v?.priceUsd}). Want one alongside?`,
        reason: "signature whole cake, paired with companion whole cake",
      };
    }
  }

  if (totalUsd >= 80) {
    return {
      kind: "delivery_note",
      name: "Local delivery",
      message:
        "For an order this size we can quote local Sugar Land delivery — share an address and we'll add it.",
      reason: "order_total >= $80, delivery worth offering",
    };
  }

  return null;
}
