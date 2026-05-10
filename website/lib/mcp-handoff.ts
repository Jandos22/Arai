import type { OrderIntent } from "./order-intent";

const DEFAULT_MCP_URL = "https://www.steppebusinessclub.com/api/mcp";

type JsonRpcEnvelope = {
  result?: { content?: Array<{ text?: string }> };
  error?: { code?: number; message?: string };
};

type ToolResult = unknown;

type CatalogRow = {
  id?: string;
  variationId?: string;
  kitchenProductId?: string;
  name?: string;
  category?: string;
  variations?: Array<{ id?: string; name?: string }>;
};

export type OrderHandoffExecution = {
  mode: "owner_gate" | "offline_fixture" | "mcp_live";
  status: "skipped" | "completed" | "failed";
  decision: string;
  cashier?: {
    tool: "square_create_order";
    args: Record<string, unknown>;
    result?: ToolResult;
    orderId?: string;
  };
  kitchen?: {
    tool: "kitchen_create_ticket";
    args: Record<string, unknown>;
    result?: ToolResult;
    ticketId?: string;
  };
  error?: string;
};

function firstId(value: unknown, names: string[]): string | undefined {
  if (!value || typeof value !== "object") return undefined;
  const obj = value as Record<string, unknown>;
  for (const name of names) {
    const candidate = obj[name];
    if (typeof candidate === "string" && candidate) return candidate;
  }
  for (const key of ["order", "ticket", "data", "result"]) {
    const nested = firstId(obj[key], names);
    if (nested) return nested;
  }
  return undefined;
}

async function callMcpTool(
  name: string,
  args: Record<string, unknown>,
  token: string,
  url: string,
): Promise<ToolResult> {
  const response = await fetch(url, {
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
  });

  if (response.status === 401 || response.status === 403) {
    throw new Error(`${name}: unauthorized MCP token`);
  }
  if (response.status >= 500) {
    throw new Error(`${name}: MCP HTTP ${response.status}`);
  }

  const envelope = (await response.json()) as JsonRpcEnvelope;
  if (envelope.error) {
    throw new Error(`${name}: ${envelope.error.message ?? `RPC ${envelope.error.code}`}`);
  }

  const text = envelope.result?.content?.[0]?.text;
  if (!text) return null;

  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function normalize(value: string | undefined): string {
  return (value ?? "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function catalogRows(result: ToolResult): CatalogRow[] {
  if (!result || typeof result !== "object") return [];
  const obj = result as { catalog?: CatalogRow[]; items?: CatalogRow[] };
  const rows = Array.isArray(obj.catalog) ? obj.catalog : Array.isArray(obj.items) ? obj.items : [];
  return rows.flatMap((row) => {
    if (row.variationId) return [row];
    if (!Array.isArray(row.variations)) return [row];
    return row.variations.map((variation) => ({
      ...row,
      variationId: variation.id,
      name: variation.name ?? row.name,
    }));
  });
}

function scoreCatalogRow(intent: OrderIntent, row: CatalogRow): number {
  const wanted = normalize(`${intent.product.slug} ${intent.product.name} ${intent.product.variationName}`);
  const rowText = normalize(`${row.name} ${row.category}`);
  let score = 0;

  if (wanted.includes("medovik") || wanted.includes("honey")) {
    if (rowText.includes("honey")) score += 80;
    if (rowText.includes("whole")) score += 20;
    if (rowText.includes("slice")) score -= 15;
  }
  if (wanted.includes("pistachio") && rowText.includes("pistachio")) score += 80;
  if ((wanted.includes("custom") || wanted.includes("birthday")) && rowText.includes("custom")) score += 80;
  if ((wanted.includes("office") || wanted.includes("box") || wanted.includes("catering")) && rowText.includes("box")) {
    score += 80;
  }

  for (const token of wanted.split(" ").filter((part) => part.length > 3)) {
    if (rowText.includes(token)) score += 5;
  }

  return score;
}

async function resolveLiveCatalogArgs(
  intent: OrderIntent,
  squareArgs: Record<string, unknown>,
  kitchenPreview: Record<string, unknown>,
  token: string,
  url: string,
): Promise<{ squareArgs: Record<string, unknown>; kitchenPreview: Record<string, unknown> }> {
  const squareItems = Array.isArray(squareArgs.items) ? squareArgs.items : [];
  const firstSquareItem = squareItems[0] as { variationId?: string; quantity?: number } | undefined;
  const currentVariationId = firstSquareItem?.variationId ?? "";

  if (currentVariationId.startsWith("sq_")) {
    return { squareArgs, kitchenPreview };
  }

  const catalog = catalogRows(await callMcpTool("square_list_catalog", {}, token, url));
  const selected = catalog
    .filter((row) => row.variationId)
    .map((row) => ({ row, score: scoreCatalogRow(intent, row) }))
    .sort((a, b) => b.score - a.score)[0]?.row;

  if (!selected?.variationId) {
    return { squareArgs, kitchenPreview };
  }

  const quantity = firstSquareItem?.quantity ?? intent.product.quantity;
  const kitchenItems = Array.isArray(kitchenPreview.items) ? kitchenPreview.items : [];
  const firstKitchenItem = kitchenItems[0] as { quantity?: number } | undefined;

  return {
    squareArgs: {
      ...squareArgs,
      items: [{ variationId: selected.variationId, quantity }],
    },
    kitchenPreview: {
      ...kitchenPreview,
      items: [
        {
          productId: selected.kitchenProductId ?? selected.id ?? selected.variationId,
          quantity: firstKitchenItem?.quantity ?? quantity,
        },
      ],
    },
  };
}

export async function executeWebsiteOrderHandoff(
  intent: OrderIntent,
): Promise<OrderHandoffExecution> {
  if (intent.handoff.ownerGate.required) {
    return {
      mode: "owner_gate",
      status: "skipped",
      decision:
        intent.handoff.ownerGate.reason ??
        "Owner review required before Square or kitchen write tools run.",
    };
  }

  const token = process.env.STEPPE_MCP_TOKEN;
  if (!token) {
    return {
      mode: "offline_fixture",
      status: "skipped",
      decision:
        "STEPPE_MCP_TOKEN is not set; returning deterministic intent payload without MCP writes.",
    };
  }

  const url = process.env.STEPPE_MCP_URL ?? DEFAULT_MCP_URL;
  let squareArgs = intent.handoff.cashier.payloadPreview;
  let kitchenPreview = intent.handoff.kitchen.payloadPreview;

  try {
    ({ squareArgs, kitchenPreview } = await resolveLiveCatalogArgs(
      intent,
      squareArgs,
      kitchenPreview,
      token,
      url,
    ));
    const order = await callMcpTool("square_create_order", squareArgs, token, url);
    const orderId = firstId(order, ["orderId", "id"]);

    if (!orderId) {
      return {
        mode: "mcp_live",
        status: "failed",
        decision: "square_create_order did not return an order id; kitchen ticket was not created.",
        cashier: {
          tool: "square_create_order",
          args: squareArgs,
          result: order,
        },
      };
    }

    const kitchenArgs = {
      ...kitchenPreview,
      orderId,
    };
    const ticket = await callMcpTool("kitchen_create_ticket", kitchenArgs, token, url);
    const ticketId = firstId(ticket, ["ticketId", "id"]);

    return {
      mode: "mcp_live",
      status: "completed",
      decision: "Created Square order and kitchen ticket through MCP.",
      cashier: {
        tool: "square_create_order",
        args: squareArgs,
        result: order,
        orderId,
      },
      kitchen: {
        tool: "kitchen_create_ticket",
        args: kitchenArgs,
        result: ticket,
        ticketId,
      },
    };
  } catch (error) {
    return {
      mode: "mcp_live",
      status: "failed",
      decision: "MCP handoff failed after website order intent capture.",
      error: error instanceof Error ? error.message : "Unknown MCP handoff error",
    };
  }
}
