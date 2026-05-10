import { NextRequest } from "next/server";
import { createOrderIntent } from "@/lib/order-intent";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const intent = createOrderIntent({ ...body, source: "website" });
    return Response.json({ ok: true, intent }, { status: 201 });
  } catch (error) {
    return Response.json(
      { ok: false, error: error instanceof Error ? error.message : "Invalid order intent" },
      { status: 400 },
    );
  }
}
