import { loadCatalog } from "@/lib/catalog";

export const dynamic = "force-static";

export function GET() {
  const catalog = loadCatalog();
  return Response.json(
    {
      ...catalog,
      _description:
        "Agent-readable HappyCake US catalog. Source of truth: square_list_catalog (sandbox MCP). " +
        "Use the /products/<slug> page for human reading; use this endpoint for programmatic access. " +
        "Use /api/availability before making stock or pickup timing claims.",
      _availabilityEndpoint: "/api/availability",
      _orderPath: {
        whatsapp: "https://wa.me/12819798320",
        instagram: "https://instagram.com/happycakeus",
        notes:
          "Order is confirmed by message before the kitchen starts. Lead times listed per item are estimates and must be checked against /api/availability.",
      },
    },
    { headers: { "Cache-Control": "public, max-age=300" } }
  );
}
