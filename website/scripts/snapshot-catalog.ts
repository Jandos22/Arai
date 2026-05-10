/**
 * Snapshot the live Happy Cake catalog from the sandbox MCP and write it to
 * data/catalog.json. Falls back to fixture if STEPPE_MCP_TOKEN is missing
 * (so dev and `npm run build` don't fail on a cold checkout).
 *
 * Usage:
 *   set -a; source ../.env.local; set +a
 *   npm run snapshot:catalog
 */
import fs from "node:fs";
import path from "node:path";

type ToolEnvelope = {
  result?: { content?: Array<{ type: string; text: string }> };
  error?: { code: number; message: string };
};

const url = process.env.STEPPE_MCP_URL ?? "https://www.steppebusinessclub.com/api/mcp";
const token = process.env.STEPPE_MCP_TOKEN;
const out = path.join(process.cwd(), "data", "catalog.json");

async function callTool<T = unknown>(name: string, args: Record<string, unknown> = {}): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-Team-Token": token ?? "",
    },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: Math.floor(Math.random() * 1e6),
      method: "tools/call",
      params: { name, arguments: args },
    }),
  });
  const env: ToolEnvelope = await res.json();
  if (env.error) throw new Error(`${name}: ${env.error.message}`);
  const text = env.result?.content?.[0]?.text;
  if (!text) throw new Error(`${name}: empty result`);
  return JSON.parse(text) as T;
}

function slugify(name: string): string {
  return name
    .toLowerCase()
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

type RawItem = {
  id: string;
  name: string;
  description?: string;
  category?: string;
  imageUrl?: string;
  variations?: Array<{ id: string; name: string; priceUsd: number; available?: boolean }>;
  leadTimeMinutes?: number;
  allergens?: string[];
  variationId?: string;
  priceCents?: number;
  kitchenProductId?: string;
};

async function main() {
  if (!token) {
    console.warn("STEPPE_MCP_TOKEN missing — leaving fixture in place. Skipping snapshot.");
    return;
  }
  console.log(`Snapshotting catalog from ${url} ...`);
  const catalog = await callTool<{ items?: RawItem[]; catalog?: RawItem[] }>("square_list_catalog", {});
  const rows = catalog.items ?? catalog.catalog ?? [];
  const items = rows.map((raw) => ({
    id: raw.id,
    slug: slugify(raw.name),
    name: raw.name,
    description: raw.description ?? "",
    category: raw.category ?? "signature",
    imageUrl: raw.imageUrl,
    kitchenProductId: raw.kitchenProductId,
    variations:
      raw.variations ??
      (raw.variationId
        ? [
            {
              id: raw.variationId,
              name: raw.name,
              priceUsd: Number(((raw.priceCents ?? 0) / 100).toFixed(2)),
              available: true,
            },
          ]
        : []),
    leadTimeMinutes: raw.leadTimeMinutes,
    allergens: raw.allergens,
  }));
  const snapshot = {
    source: "mcp-snapshot" as const,
    capturedAt: new Date().toISOString(),
    items,
  };
  fs.writeFileSync(out, JSON.stringify(snapshot, null, 2) + "\n");
  console.log(`Wrote ${items.length} items to ${out}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
