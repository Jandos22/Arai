import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const paymentIntentId = String(body.paymentIntentId ?? "").trim();
    if (!paymentIntentId.startsWith("pay_")) {
      throw new Error("Invalid mock payment intent id.");
    }

    return Response.json({
      ok: true,
      payment: {
        paymentIntentId,
        provider: "square_sandbox_mock",
        status: "paid",
        paidAt: new Date().toISOString(),
      },
      nextStep:
        "Payment marked paid in the mock provider. Production should receive this from a signed Square webhook before kitchen prep starts.",
    });
  } catch (error) {
    return Response.json(
      { ok: false, error: error instanceof Error ? error.message : "Invalid payment confirmation" },
      { status: 400 },
    );
  }
}
