import { loadCatalog } from "@/lib/catalog";
import type { CampaignAttributionInput } from "@/lib/order-intent";
import OrderForm from "./OrderForm";

export const metadata = {
  title: "Order intent",
  description: "Capture a HappyCake pickup or delivery order intent and route it toward cashier and kitchen handoff.",
};

type OrderSearchParams = {
  product?: string;
  landingPath?: string;
  campaign?: string;
  campaignId?: string;
  channel?: string;
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  utm_term?: string;
  utm_content?: string;
};

function attributionFromSearchParams(params: OrderSearchParams): CampaignAttributionInput | undefined {
  const attribution = {
    landingPath: params.landingPath,
    campaign: params.campaign,
    campaignId: params.campaignId,
    channel: params.channel,
    utm_source: params.utm_source,
    utm_medium: params.utm_medium,
    utm_campaign: params.utm_campaign,
    utm_term: params.utm_term,
    utm_content: params.utm_content,
  };

  return Object.values(attribution).some(Boolean) ? attribution : undefined;
}

export default async function OrderPage({ searchParams }: { searchParams: Promise<OrderSearchParams> }) {
  const params = await searchParams;
  const catalog = loadCatalog();
  const attribution = attributionFromSearchParams(params);
  return (
    <div className="space-y-8">
      <div className="max-w-3xl">
        <p className="uppercase tracking-widest text-xs text-happy-blue-500 font-medium">Website order intake</p>
        <h1 className="font-display text-4xl text-happy-blue-900 mt-2">Start an order</h1>
        <p className="mt-4 text-ink/75">Pick a cake, choose pickup or delivery, and request a time now or later. The site captures a structured order intent with the exact POS/kitchen handoff contract, then owner-gates custom, allergy, complaint, incomplete delivery, or high-value cases.</p>
      </div>
      <OrderForm items={catalog.items} initialSlug={params.product} initialAttribution={attribution} />
    </div>
  );
}
