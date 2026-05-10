import { loadCustomerProfile, maskPaymentToken } from "@/lib/customers";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const profile = await loadCustomerProfile(decodeURIComponent(id));
  if (!profile) {
    return Response.json(
      { error: "not_found", id, _description: "No saved profile for this identifier yet." },
      { status: 404 }
    );
  }
  return Response.json(
    {
      ...profile,
      paymentDisplay: maskPaymentToken(profile.paymentToken),
      _description:
        "Sandbox customer profile. Source: orchestrator/customers.py JSON store. " +
        "Profiles are auto-created on every WhatsApp/Instagram inbound — no signup needed. " +
        "paymentDisplay is masked; raw paymentToken is a sandbox-only opaque string.",
      _quickReorderEndpoint: profile.favoriteProduct
        ? `/order?product=${encodeURIComponent(profile.favoriteProduct.sku)}&customer=${encodeURIComponent(profile.id)}&channel=quick-reorder`
        : null,
    },
    { headers: { "Cache-Control": "no-store" } }
  );
}
