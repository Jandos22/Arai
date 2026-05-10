// Catalog loader. Reads from data/catalog.json (snapshotted from MCP).
// Falls back to fixture if snapshot missing — keeps dev UX clean before MCP
// snapshot has been run.
import fs from "node:fs";
import path from "node:path";

export type CatalogVariation = {
  id: string;
  name: string;
  priceUsd: number;
  available?: boolean;
};

export type CatalogItem = {
  id: string;
  slug: string;
  name: string;
  description: string;
  category: string;
  kitchenProductId?: string;
  imageUrl?: string | null;
  imageAlt?: string | null;
  variations: CatalogVariation[];
  leadTimeMinutes?: number;
  allergens?: string[];
};

export type Catalog = {
  source: "mcp-snapshot" | "fixture";
  capturedAt: string;
  items: CatalogItem[];
};

let cached: Catalog | null = null;

export function loadCatalog(): Catalog {
  if (cached) return cached;
  const snapshot = path.join(process.cwd(), "data", "catalog.json");
  const fixture = path.join(process.cwd(), "data", "catalog.fixture.json");
  const file = fs.existsSync(snapshot) ? snapshot : fixture;
  const raw = fs.readFileSync(file, "utf-8");
  cached = JSON.parse(raw) as Catalog;
  return cached;
}

export function findBySlug(slug: string): CatalogItem | undefined {
  return loadCatalog().items.find((i) => i.slug === slug);
}

export function priceRange(item: CatalogItem): { min: number; max: number } {
  const prices = item.variations.map((v) => v.priceUsd);
  return { min: Math.min(...prices), max: Math.max(...prices) };
}
