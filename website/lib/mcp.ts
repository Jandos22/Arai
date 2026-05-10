const DEFAULT_MCP_URL = "https://www.steppebusinessclub.com/api/mcp";

type ToolEnvelope = {
  result?: { content?: Array<{ type?: string; text?: string }> };
  error?: { code?: number; message?: string };
};

export type McpEvidence = {
  tool: string;
  source: "mcp";
  ok: boolean;
  summary?: unknown;
  error?: string;
};

export function isMcpConfigured(): boolean {
  return Boolean(process.env.STEPPE_MCP_TOKEN);
}

export async function callMcpTool<T = unknown>(
  name: string,
  args: Record<string, unknown> = {},
): Promise<T> {
  const token = process.env.STEPPE_MCP_TOKEN;
  if (!token) {
    throw new Error("STEPPE_MCP_TOKEN is not configured");
  }

  const res = await fetch(process.env.STEPPE_MCP_URL ?? DEFAULT_MCP_URL, {
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

  if (!res.ok) {
    throw new Error(`${name}: HTTP ${res.status}`);
  }

  const envelope = (await res.json()) as ToolEnvelope;
  if (envelope.error) {
    throw new Error(`${name}: ${envelope.error.message ?? "MCP error"}`);
  }

  const text = envelope.result?.content?.[0]?.text;
  if (!text) return undefined as T;

  try {
    return JSON.parse(text) as T;
  } catch {
    return text as T;
  }
}

export async function readMcpEvidence<T = unknown>(
  tool: string,
  args: Record<string, unknown> = {},
  summarize: (result: T) => unknown = (result) => result,
): Promise<{ result?: T; evidence: McpEvidence }> {
  try {
    const result = await callMcpTool<T>(tool, args);
    return {
      result,
      evidence: {
        tool,
        source: "mcp",
        ok: true,
        summary: summarize(result),
      },
    };
  } catch (error) {
    return {
      evidence: {
        tool,
        source: "mcp",
        ok: false,
        error: error instanceof Error ? error.message : `${tool}: MCP call failed`,
      },
    };
  }
}
