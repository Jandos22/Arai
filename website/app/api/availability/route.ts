import { loadAvailability } from "@/lib/availability";

export const dynamic = "force-dynamic";

export async function GET() {
  const availability = await loadAvailability();
  return Response.json(
    {
      ...availability,
      _description:
        "Agent-readable inventory and kitchen capacity. Live mode calls square_get_inventory and kitchen_get_capacity when STEPPE_MCP_TOKEN is configured. Fallback mode is intentionally conservative and must not be treated as a pickup promise.",
    },
    { headers: { "Cache-Control": "no-store" } },
  );
}
