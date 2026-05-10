import { NextRequest } from "next/server";
import { createOrderIntent } from "@/lib/order-intent";
import { executeWebsiteOrderHandoff } from "@/lib/mcp-handoff";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const intent = createOrderIntent({ ...body, source: "website" });
    const handoff = await executeWebsiteOrderHandoff(intent);
    const ok = handoff.status !== "failed";
    return Response.json({ ok, intent, handoff }, { status: ok ? 201 : 502 });
  } catch (error) {
    return Response.json(
      { ok: false, error: error instanceof Error ? error.message : "Invalid order intent" },
      { status: 400 },
    );
  }
}
