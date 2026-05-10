import { loadCatalog, type CatalogItem, type CatalogVariation } from "./catalog";

const DEFAULT_MCP_URL = "https://www.steppebusinessclub.com/api/mcp";
const FALLBACK_PICKUP_COPY =
  "Live kitchen capacity is unavailable. Request a pickup window and wait for confirmation before promising same-day timing.";

type ToolEnvelope = {
  result?: { content?: Array<{ type?: string; text?: string }> };
  error?: { code?: number; message?: string };
};

type ToolState = "live" | "unconfigured" | "error";

export type VariationInventory = {
  variationId: string;
  quantity: number | null;
  inStock: boolean | null;
  label: string;
  source: "square_get_inventory" | "catalog-fallback";
};

export type KitchenCapacity = {
  remainingCapacityMinutes: number | null;
  dailyCapacityMinutes: number | null;
  activePrepMinutes: number | null;
  defaultLeadTimeMinutes: number;
  canPromiseSameDay: boolean | null;
  label: string;
  source: "kitchen_get_capacity" | "fallback";
};

export type AvailabilitySnapshot = {
  capturedAt: string;
  source: "mcp-live" | "partial-live" | "conservative-fallback";
  tools: {
    square_get_inventory: ToolState;
    kitchen_get_capacity: ToolState;
  };
  inventory: VariationInventory[];
  capacity: KitchenCapacity;
  customerPromise: string;
  agentGuidance: string[];
  errors?: string[];
};

type RawRecord = Record<string, unknown>;

function isRecord(value: unknown): value is RawRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function numeric(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

function booleanish(value: unknown): boolean | null {
  if (typeof value === "boolean") return value;
  if (typeof value !== "string") return null;
  const normalized = value.toLowerCase();
  if (["true", "available", "in_stock", "instock", "ok"].includes(normalized)) return true;
  if (["false", "sold_out", "out_of_stock", "out", "unavailable"].includes(normalized)) return false;
  return null;
}

async function callMcpTool<T>(name: string, args: Record<string, unknown>): Promise<T> {
  const token = process.env.STEPPE_MCP_TOKEN;
  if (!token) throw new Error("STEPPE_MCP_TOKEN is not configured");

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 2500);
  try {
    const response = await fetch(process.env.STEPPE_MCP_URL ?? DEFAULT_MCP_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        "X-Team-Token": token,
      },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: Math.floor(Math.random() * 1e9),
        method: "tools/call",
        params: { name, arguments: args },
      }),
      cache: "no-store",
      signal: controller.signal,
    });
    const envelope = (await response.json()) as ToolEnvelope;
    if (envelope.error) throw new Error(envelope.error.message ?? `${name} failed`);
    const text = envelope.result?.content?.[0]?.text;
    if (!text) throw new Error(`${name} returned no content`);
    return JSON.parse(text) as T;
  } finally {
    clearTimeout(timeout);
  }
}

function variationIds(items: CatalogItem[]): string[] {
  return items.flatMap((item) => item.variations.map((variation) => variation.id));
}

function inventoryRows(raw: unknown): RawRecord[] {
  if (Array.isArray(raw)) return raw.filter(isRecord);
  if (!isRecord(raw)) return [];
  for (const key of ["inventory", "counts", "items", "variations", "objects"]) {
    const value = raw[key];
    if (Array.isArray(value)) return value.filter(isRecord);
  }
  return [];
}

function inventoryId(row: RawRecord): string | null {
  for (const key of ["variationId", "variation_id", "catalogObjectId", "catalog_object_id", "id", "sku"]) {
    const value = row[key];
    if (typeof value === "string" && value) return value;
  }
  return null;
}

function inventoryQuantity(row: RawRecord): number | null {
  for (const key of ["quantity", "quantityAvailable", "availableQuantity", "onHand", "count", "qty"]) {
    const value = numeric(row[key]);
    if (value !== null) return value;
  }
  return null;
}

function inventoryAvailable(row: RawRecord, quantity: number | null): boolean | null {
  for (const key of ["available", "inStock", "isAvailable", "status", "state"]) {
    const value = booleanish(row[key]);
    if (value !== null) return value;
  }
  return quantity === null ? null : quantity > 0;
}

function fallbackInventory(items: CatalogItem[]): VariationInventory[] {
  return items.flatMap((item) =>
    item.variations.map((variation) => ({
      variationId: variation.id,
      quantity: null,
      inStock: variation.available === false ? false : null,
      label:
        variation.available === false
          ? "Not listed as available"
          : "Listed in catalog; live stock must be confirmed",
      source: "catalog-fallback" as const,
    })),
  );
}

function normalizeInventory(raw: unknown, items: CatalogItem[]): VariationInventory[] {
  const rows = new Map(inventoryRows(raw).map((row) => [inventoryId(row), row]));
  return items.flatMap((item) =>
    item.variations.map((variation: CatalogVariation) => {
      const row = rows.get(variation.id) ?? null;
      if (!row) {
        return {
          variationId: variation.id,
          quantity: null,
          inStock: null,
          label: "Live stock unknown; confirm before promising",
          source: "square_get_inventory" as const,
        };
      }
      const quantity = inventoryQuantity(row);
      const inStock = inventoryAvailable(row, quantity);
      return {
        variationId: variation.id,
        quantity,
        inStock,
        label:
          inStock === true
            ? quantity === null
              ? "Live stock available"
              : `${quantity} available in live stock`
            : inStock === false
              ? "Sold out in live stock"
              : "Live stock unknown; confirm before promising",
        source: "square_get_inventory",
      };
    }),
  );
}

function normalizeCapacity(raw: unknown): KitchenCapacity {
  const record = isRecord(raw) ? raw : {};
  const remainingCapacityMinutes = numeric(
    record.remainingCapacityMinutes ?? record.remainingCapacity ?? record.capacityRemainingMinutes,
  );
  const dailyCapacityMinutes = numeric(
    record.dailyCapacityMinutes ?? record.totalCapacityMinutes ?? record.capacityMinutes,
  );
  const activePrepMinutes = numeric(record.activePrepMinutes ?? record.usedCapacityMinutes ?? record.currentLoadMinutes);
  const defaultLeadTimeMinutes =
    numeric(record.defaultLeadTimeMinutes ?? record.leadTimeMinutes ?? record.defaultPrepMinutes) ?? 90;
  const canPromiseSameDay =
    remainingCapacityMinutes === null ? null : remainingCapacityMinutes >= defaultLeadTimeMinutes;

  return {
    remainingCapacityMinutes,
    dailyCapacityMinutes,
    activePrepMinutes,
    defaultLeadTimeMinutes,
    canPromiseSameDay,
    label:
      remainingCapacityMinutes === null
        ? "Kitchen capacity returned without remaining minutes; confirm timing"
        : canPromiseSameDay
          ? `${remainingCapacityMinutes} prep minutes open today`
          : `Only ${remainingCapacityMinutes} prep minutes open; avoid same-day promises`,
    source: "kitchen_get_capacity",
  };
}

function fallbackCapacity(): KitchenCapacity {
  return {
    remainingCapacityMinutes: null,
    dailyCapacityMinutes: null,
    activePrepMinutes: null,
    defaultLeadTimeMinutes: 90,
    canPromiseSameDay: null,
    label: "Live kitchen capacity unavailable",
    source: "fallback",
  };
}

function customerPromise(capacity: KitchenCapacity): string {
  if (capacity.source === "fallback") return FALLBACK_PICKUP_COPY;
  if (capacity.canPromiseSameDay === false) {
    return "Kitchen capacity is tight right now. Ask for a pickup window and wait for confirmation before taking the order.";
  }
  if (capacity.canPromiseSameDay === true) {
    return "Live kitchen capacity has room for standard prep, but pickup still needs confirmation before charging.";
  }
  return "Live kitchen capacity was reached, but timing still needs confirmation before promising pickup.";
}

export async function loadAvailability(): Promise<AvailabilitySnapshot> {
  const catalog = loadCatalog();
  const ids = variationIds(catalog.items);
  const hasToken = Boolean(process.env.STEPPE_MCP_TOKEN);
  const capturedAt = new Date().toISOString();

  if (!hasToken) {
    const capacity = fallbackCapacity();
    return {
      capturedAt,
      source: "conservative-fallback",
      tools: { square_get_inventory: "unconfigured", kitchen_get_capacity: "unconfigured" },
      inventory: fallbackInventory(catalog.items),
      capacity,
      customerPromise: customerPromise(capacity),
      agentGuidance: [
        "Do not describe any item as in stock unless /api/availability reports live square_get_inventory data.",
        "Do not promise pickup timing unless /api/availability reports live kitchen_get_capacity data with enough remaining minutes.",
      ],
    };
  }

  const errors: string[] = [];
  const [inventoryResult, capacityResult] = await Promise.allSettled([
    callMcpTool("square_get_inventory", { variationIds: ids }),
    callMcpTool("kitchen_get_capacity", {}),
  ]);

  const inventory =
    inventoryResult.status === "fulfilled"
      ? normalizeInventory(inventoryResult.value, catalog.items)
      : fallbackInventory(catalog.items);
  if (inventoryResult.status === "rejected") errors.push(`square_get_inventory: ${inventoryResult.reason}`);

  const capacity =
    capacityResult.status === "fulfilled" ? normalizeCapacity(capacityResult.value) : fallbackCapacity();
  if (capacityResult.status === "rejected") errors.push(`kitchen_get_capacity: ${capacityResult.reason}`);

  const inventoryLive = inventoryResult.status === "fulfilled";
  const capacityLive = capacityResult.status === "fulfilled";

  return {
    capturedAt,
    source: inventoryLive && capacityLive ? "mcp-live" : "partial-live",
    tools: {
      square_get_inventory: inventoryLive ? "live" : "error",
      kitchen_get_capacity: capacityLive ? "live" : "error",
    },
    inventory,
    capacity,
    customerPromise: customerPromise(capacity),
    agentGuidance: [
      inventoryLive
        ? "Use variation-level live inventory labels from square_get_inventory."
        : "Inventory is fallback only; ask staff to confirm stock.",
      capacityLive
        ? "Use kitchen_get_capacity remaining minutes as the upper bound for pickup guidance."
        : "Capacity is fallback only; do not promise same-day timing.",
    ],
    errors: errors.length ? errors : undefined,
  };
}

export function inventoryForItem(
  snapshot: AvailabilitySnapshot,
  item: CatalogItem,
): VariationInventory[] {
  const byId = new Map(snapshot.inventory.map((entry) => [entry.variationId, entry]));
  return item.variations.map(
    (variation) =>
      byId.get(variation.id) ?? {
        variationId: variation.id,
        quantity: null,
        inStock: null,
        label: "Live stock unknown; confirm before promising",
        source: "catalog-fallback",
      },
  );
}

export function itemAvailabilityLabel(snapshot: AvailabilitySnapshot, item: CatalogItem): string {
  const entries = inventoryForItem(snapshot, item);
  if (entries.some((entry) => entry.source === "square_get_inventory" && entry.inStock === true)) {
    return "Live stock seen";
  }
  if (entries.every((entry) => entry.inStock === false)) return "No stock listed";
  return "Confirm stock";
}
