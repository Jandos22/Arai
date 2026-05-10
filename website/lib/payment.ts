import type { OrderIntent } from "./order-intent";

export type PaymentIntentInput = {
  orderIntentId?: string | null;
  amountUsd?: number | null;
  customerName?: string | null;
  contact?: string | null;
  returnPath?: string | null;
  source?: "website" | "assistant" | "agent" | null;
};

export type PaymentIntent = {
  paymentIntentId: string;
  provider: "square_sandbox_mock";
  status: "payment_link_created" | "paid";
  mode: "mock_provider_hosted_checkout";
  amountUsd: number;
  currency: "USD";
  orderIntentId?: string;
  customerName?: string;
  contact?: string;
  paymentUrl: string;
  confirmationUrl: string;
  rules: {
    noCardDataCollectedByArai: true;
    productionProvider: "Square Checkout API or Square Payment Links";
    kitchenPrepRule: "Do not start kitchen prep until payment status is paid or owner explicitly approves pay-later.";
  };
};

function safeText(value: string | null | undefined): string | undefined {
  const text = (value ?? "").toString().trim().slice(0, 500);
  return text || undefined;
}

function safeAmount(value: number | null | undefined): number {
  const amount = Number(value ?? 0);
  if (!Number.isFinite(amount) || amount <= 0) return 0;
  return Number(amount.toFixed(2));
}

function baseUrl(): string {
  return process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
}

export function createPaymentIntent(input: PaymentIntentInput): PaymentIntent {
  const amountUsd = safeAmount(input.amountUsd);
  if (!amountUsd) {
    throw new Error("Payment amount must be greater than 0.");
  }

  const orderIntentId = safeText(input.orderIntentId);
  const paymentIntentId = `pay_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
  const url = new URL("/pay", baseUrl());
  url.searchParams.set("paymentIntentId", paymentIntentId);
  url.searchParams.set("amountUsd", amountUsd.toFixed(2));
  if (orderIntentId) url.searchParams.set("orderIntentId", orderIntentId);

  return {
    paymentIntentId,
    provider: "square_sandbox_mock",
    status: "payment_link_created",
    mode: "mock_provider_hosted_checkout",
    amountUsd,
    currency: "USD",
    orderIntentId,
    customerName: safeText(input.customerName),
    contact: safeText(input.contact),
    paymentUrl: url.toString(),
    confirmationUrl: "/api/payment-intent/confirm",
    rules: {
      noCardDataCollectedByArai: true,
      productionProvider: "Square Checkout API or Square Payment Links",
      kitchenPrepRule: "Do not start kitchen prep until payment status is paid or owner explicitly approves pay-later.",
    },
  };
}

export function createPaymentIntentFromOrder(intent: OrderIntent): PaymentIntent {
  return createPaymentIntent({
    orderIntentId: intent.intentId,
    amountUsd: intent.product.estimatedTotalUsd,
    customerName: intent.customer.name,
    contact: intent.customer.contact,
    source: intent.source,
  });
}
