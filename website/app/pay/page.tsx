import MockPayButton from "./MockPayButton";

export const metadata = {
  title: "Mock payment - HappyCake US",
  description: "Provider-hosted checkout mock for HappyCake order-intent demos.",
};

type PaySearchParams = {
  paymentIntentId?: string;
  amountUsd?: string;
  orderIntentId?: string;
};

export default async function PayPage({ searchParams }: { searchParams: Promise<PaySearchParams> }) {
  const params = await searchParams;
  const amount = params.amountUsd ? Number(params.amountUsd).toFixed(2) : "0.00";

  return (
    <div className="mx-auto max-w-xl space-y-8">
      <header>
        <p className="uppercase tracking-widest text-xs text-happy-blue-500 font-medium">
          Mock provider checkout
        </p>
        <h1 className="mt-2 font-display text-4xl text-happy-blue-900">HappyCake payment link</h1>
        <p className="mt-4 text-ink/75">
          This page simulates a Square-hosted checkout link. Arai never collects card numbers;
          production should replace this mock with Square Checkout or Square Payment Links.
        </p>
      </header>

      <section className="rounded-2xl border border-happy-blue-200 bg-white p-6">
        <div className="grid gap-4 text-sm">
          <div className="flex items-center justify-between border-b border-cream-200 pb-3">
            <span className="text-ink/60">Payment intent</span>
            <span className="font-mono text-xs text-happy-blue-900">
              {params.paymentIntentId ?? "missing"}
            </span>
          </div>
          <div className="flex items-center justify-between border-b border-cream-200 pb-3">
            <span className="text-ink/60">Order intent</span>
            <span className="font-mono text-xs text-happy-blue-900">
              {params.orderIntentId ?? "not attached"}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-ink/60">Amount</span>
            <span className="font-display text-3xl text-happy-blue-900">${amount}</span>
          </div>
        </div>
        <div className="mt-6">
          <MockPayButton paymentIntentId={params.paymentIntentId} />
        </div>
        <p className="mt-4 text-xs leading-relaxed text-ink/60">
          In production, payment confirmation must come from a signed Square webhook. This demo button
          is visual only so agents can discover the hosted-checkout shape without card handling.
        </p>
      </section>
    </div>
  );
}
