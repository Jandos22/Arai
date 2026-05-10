import { promises as fs } from "node:fs";
import path from "node:path";

/**
 * Sandbox-only customer profile loader. Reads the JSON file written by the
 * orchestrator (`evidence/customers.json`). Never includes real PAN data —
 * `paymentToken` is an opaque sandbox string like "sandbox_card_visa_4242".
 *
 * For production, replace with a server-side fetch against your real
 * customer service. See docs/PRODUCTION-PATH.md.
 */
export type CustomerProfile = {
  id: string;
  name?: string;
  channelKeys?: Record<string, string>;
  deliveryAddress?: string;
  paymentToken?: string;
  favoriteProduct?: { sku: string; count: number };
  lastOrders?: Array<{ id: string; sku: string; ts: string }>;
  firstSeen?: string;
  lastSeen?: string;
};

const STORE_PATH = path.resolve(process.cwd(), "..", "evidence", "customers.json");

export async function loadCustomerProfile(id: string): Promise<CustomerProfile | null> {
  try {
    const raw = await fs.readFile(STORE_PATH, "utf-8");
    const data = JSON.parse(raw || "{}") as Record<string, Record<string, unknown>>;
    const profile = data[id];
    if (!profile) return null;
    return normalize(id, profile);
  } catch {
    return null;
  }
}

function normalize(id: string, raw: Record<string, unknown>): CustomerProfile {
  return {
    id,
    name: typeof raw.name === "string" ? raw.name : undefined,
    channelKeys: (raw.channel_keys as Record<string, string>) ?? undefined,
    deliveryAddress: typeof raw.delivery_address === "string" ? raw.delivery_address : undefined,
    paymentToken: typeof raw.payment_token === "string" ? raw.payment_token : undefined,
    favoriteProduct: raw.favorite_product as CustomerProfile["favoriteProduct"],
    lastOrders: (raw.last_orders as CustomerProfile["lastOrders"]) ?? [],
    firstSeen: typeof raw.first_seen === "string" ? raw.first_seen : undefined,
    lastSeen: typeof raw.last_seen === "string" ? raw.last_seen : undefined,
  };
}

export function maskPaymentToken(token?: string): string {
  if (!token) return "—";
  // sandbox_card_visa_4242 → "Visa ending 4242"
  const m = token.match(/^sandbox_card_(\w+)_(\d{4})$/);
  if (m) return `${m[1][0].toUpperCase()}${m[1].slice(1)} ending ${m[2]}`;
  return token.slice(0, 4) + "•••" + token.slice(-4);
}
