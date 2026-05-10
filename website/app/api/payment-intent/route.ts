import { NextRequest } from "next/server";
import { createPaymentIntent } from "@/lib/payment";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const payment = createPaymentIntent({
      orderIntentId: body.orderIntentId,
      amountUsd: body.amountUsd,
      customerName: body.customerName,
      contact: body.contact,
      returnPath: body.returnPath,
      source: body.source ?? "agent",
    });

    return Response.json({ ok: true, payment }, { status: 201 });
  } catch (error) {
    return Response.json(
      { ok: false, error: error instanceof Error ? error.message : "Invalid payment intent" },
      { status: 400 },
    );
  }
}
