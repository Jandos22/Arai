export const metadata = {
  title: "Agent guide - HappyCake US",
  description:
    "How AI agents can read HappyCake catalog, policies, availability, and capture pickup or delivery order intents.",
};

const endpointRows = [
  {
    label: "Discover",
    path: "/agent.json",
    body: "Capabilities, endpoint map, order-intent shape, owner-gate rules, and fulfillment hints.",
  },
  {
    label: "Index",
    path: "/llms.txt",
    body: "Curated plain-text map of the most useful pages and APIs for agent reading.",
  },
  {
    label: "Catalog",
    path: "/api/catalog",
    body: "Product names, slugs, variations, price ranges, lead times, and allergen notes.",
  },
  {
    label: "Availability",
    path: "/api/availability",
    body: "Inventory and kitchen capacity status. Treat fallback mode as unconfirmed.",
  },
  {
    label: "Policies",
    path: "/api/policies",
    body: "Ordering, pickup, delivery, allergen, return, and escalation rules.",
  },
  {
    label: "Order intent",
    path: "/api/order-intent",
    body: "POST structured pickup or delivery intent for later cashier, payment, and kitchen handoff.",
  },
  {
    label: "Payment intent",
    path: "/api/payment-intent",
    body: "POST amount and order intent id to create a mock provider-hosted payment link.",
  },
];

const payload = `{
  "productSlug": "honey-medovik",
  "quantity": 1,
  "customerName": "Hermes Customer",
  "contact": "+1 281 555 0100",
  "fulfillmentType": "delivery",
  "deliveryAddress": "123 Main St, Sugar Land, TX 77479",
  "pickupDate": "2026-05-12",
  "pickupTime": "16:30",
  "notes": "Birthday dinner. No allergy promise requested."
}`;

const paymentPayload = `{
  "orderIntentId": "web_mock_123",
  "amountUsd": 46,
  "customerName": "Hermes Customer",
  "contact": "+1 281 555 0100",
  "source": "agent"
}`;

export default function AgentsPage() {
  return (
    <div className="space-y-12">
      <header className="max-w-3xl">
        <p className="uppercase tracking-widest text-xs text-happy-blue-500 font-medium">
          Agent access
        </p>
        <h1 className="mt-2 font-display text-4xl text-happy-blue-900">
          Arai-ready ordering for AI agents.
        </h1>
        <p className="mt-4 text-ink/75">
          Hermes, OpenClaw-managed browser agents, and other assistants should use the machine-readable
          endpoints below before making claims about stock, pickup timing, delivery, allergens, or
          order status.
        </p>
      </header>

      <section className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {endpointRows.map((row) => (
          <a
            key={row.path}
            href={row.path}
            className="rounded-2xl border border-happy-blue-200 bg-white p-5 hover:bg-cream-100 transition"
          >
            <p className="text-xs uppercase tracking-widest text-happy-blue-500 font-medium">
              {row.label}
            </p>
            <h2 className="mt-2 font-display text-xl text-happy-blue-900">{row.path}</h2>
            <p className="mt-2 text-sm leading-relaxed text-ink/70">{row.body}</p>
          </a>
        ))}
      </section>

      <section className="grid lg:grid-cols-[0.9fr_1.1fr] gap-8">
        <div>
          <p className="uppercase tracking-widest text-xs text-happy-blue-500 font-medium">
            Order flow
          </p>
          <h2 className="mt-2 font-display text-3xl text-happy-blue-900">
            Pickup, delivery, and scheduled later.
          </h2>
          <div className="mt-5 space-y-4 text-sm leading-relaxed text-ink/75">
            <p>
              First read <a className="text-happy-blue-700 hover:text-happy-blue-900" href="/agent.json">/agent.json</a>,
              then check catalog, policies, and availability. If availability is in fallback mode,
              ask for confirmation instead of promising same-day fulfillment.
            </p>
            <p>
              Submit order intent only after collecting cake, size, quantity, contact, fulfillment
              mode, requested date/time, and delivery address when needed. Custom decoration, allergy
              promises, complaints, incomplete delivery details, and high-value orders route through
              owner review before Square, payment, or kitchen writes.
            </p>
            <p>
              For payment, use the returned mock payment link or call <a className="text-happy-blue-700 hover:text-happy-blue-900" href="/api/payment-intent">/api/payment-intent</a>.
              The link simulates provider-hosted checkout; Arai does not collect card data.
              Production should swap the mock for Square Checkout or Square Payment Links and rely on
              signed Square webhooks before kitchen prep starts.
            </p>
          </div>
        </div>
        <div className="grid gap-4">
          <pre className="overflow-auto rounded-2xl bg-happy-blue-900 p-5 text-xs leading-relaxed text-cream-50">
            {payload}
          </pre>
          <pre className="overflow-auto rounded-2xl bg-happy-blue-900 p-5 text-xs leading-relaxed text-cream-50">
            {paymentPayload}
          </pre>
        </div>
      </section>
    </div>
  );
}
