import { loadCatalog } from "@/lib/catalog";
import OrderForm from "./OrderForm";

export const metadata = {
  title: "Order intent",
  description: "Capture a HappyCake website order intent and route it toward cashier and kitchen handoff.",
};

export default async function OrderPage({ searchParams }: { searchParams: Promise<{ product?: string }> }) {
  const params = await searchParams;
  const catalog = loadCatalog();
  return (
    <div className="space-y-8">
      <div className="max-w-3xl">
        <p className="uppercase tracking-widest text-xs text-happy-blue-500 font-medium">Website order intake</p>
        <h1 className="font-display text-4xl text-happy-blue-900 mt-2">Start an order</h1>
        <p className="mt-4 text-ink/75">Pick a cake and pickup window. The site captures a structured order intent with the exact POS/kitchen handoff contract, then owner-gates custom, allergy, complaint, or high-value cases.</p>
      </div>
      <OrderForm items={catalog.items} initialSlug={params.product} />
    </div>
  );
}
