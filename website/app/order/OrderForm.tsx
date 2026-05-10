"use client";

import { FormEvent, useMemo, useState } from "react";
import type { CatalogItem } from "@/lib/catalog";
import type { CampaignAttributionInput } from "@/lib/order-intent";

type Props = {
  items: CatalogItem[];
  initialSlug?: string;
  initialAttribution?: CampaignAttributionInput;
};

export default function OrderForm({ items, initialSlug, initialAttribution }: Props) {
  const [productSlug, setProductSlug] = useState(initialSlug ?? items[0]?.slug ?? "");
  const [variationId, setVariationId] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [customerName, setCustomerName] = useState("");
  const [contact, setContact] = useState("");
  const [pickupDate, setPickupDate] = useState("");
  const [pickupTime, setPickupTime] = useState("");
  const [notes, setNotes] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const selected = useMemo(() => items.find((i) => i.slug === productSlug) ?? items[0], [items, productSlug]);
  const variations = selected?.variations ?? [];
  const chosenVariationId = variationId || variations[0]?.id || "";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setResult(null);
    const response = await fetch("/api/order-intent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        productSlug,
        variationId: chosenVariationId,
        quantity,
        customerName,
        contact,
        pickupDate,
        pickupTime,
        notes,
        attribution: initialAttribution,
      }),
    });
    const json = await response.json();
    setResult(json);
    setLoading(false);
  }

  return (
    <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-8">
      <form onSubmit={submit} className="rounded-3xl bg-cream-100 p-6 space-y-5">
        <div>
          <label className="text-sm font-medium text-happy-blue-900">Cake</label>
          <select className="mt-2 w-full rounded-xl border border-cream-300 bg-white px-4 py-3" value={productSlug} onChange={(e) => { setProductSlug(e.target.value); setVariationId(""); }}>
            {items.map((item) => <option key={item.id} value={item.slug}>{item.name}</option>)}
          </select>
        </div>
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-happy-blue-900">Size</label>
            <select className="mt-2 w-full rounded-xl border border-cream-300 bg-white px-4 py-3" value={chosenVariationId} onChange={(e) => setVariationId(e.target.value)}>
              {variations.map((v) => <option key={v.id} value={v.id}>{v.name} · ${v.priceUsd}</option>)}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium text-happy-blue-900">Quantity</label>
            <input className="mt-2 w-full rounded-xl border border-cream-300 bg-white px-4 py-3" type="number" min={1} max={24} value={quantity} onChange={(e) => setQuantity(Number(e.target.value))} />
          </div>
        </div>
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-happy-blue-900">Name</label>
            <input className="mt-2 w-full rounded-xl border border-cream-300 bg-white px-4 py-3" value={customerName} onChange={(e) => setCustomerName(e.target.value)} placeholder="Your name" />
          </div>
          <div>
            <label className="text-sm font-medium text-happy-blue-900">Phone / WhatsApp</label>
            <input className="mt-2 w-full rounded-xl border border-cream-300 bg-white px-4 py-3" value={contact} onChange={(e) => setContact(e.target.value)} placeholder="+1 ..." />
          </div>
        </div>
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-happy-blue-900">Pickup date</label>
            <input className="mt-2 w-full rounded-xl border border-cream-300 bg-white px-4 py-3" type="date" value={pickupDate} onChange={(e) => setPickupDate(e.target.value)} />
          </div>
          <div>
            <label className="text-sm font-medium text-happy-blue-900">Pickup time</label>
            <input className="mt-2 w-full rounded-xl border border-cream-300 bg-white px-4 py-3" type="time" value={pickupTime} onChange={(e) => setPickupTime(e.target.value)} />
          </div>
        </div>
        <div>
          <label className="text-sm font-medium text-happy-blue-900">Notes</label>
          <textarea className="mt-2 w-full rounded-xl border border-cream-300 bg-white px-4 py-3" rows={4} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Occasion, allergy concerns, name-on-cake, or complaint context" />
        </div>
        <button className="rounded-full bg-happy-blue-700 text-cream-50 px-6 py-3 hover:bg-happy-blue-900 font-medium disabled:opacity-60" disabled={loading}>
          {loading ? "Capturing..." : "Capture website order intent"}
        </button>
      </form>

      <aside className="rounded-3xl border border-happy-blue-200 p-6 bg-white/70">
        <p className="uppercase tracking-widest text-xs text-happy-blue-500 font-medium">Realtime handoff preview</p>
        <h2 className="font-display text-2xl text-happy-blue-900 mt-2">Website → cashier → kitchen</h2>
        <p className="text-sm text-ink/70 mt-3">This prototype captures a structured website order intent. In production, this payload feeds Square and the kitchen capacity-aware handoff used by the orchestrator.</p>
        {initialAttribution ? (
          <div className="mt-5 rounded-2xl bg-cream-100 p-4 text-sm text-ink/75">
            <p className="font-medium text-happy-blue-900">Campaign attribution attached</p>
            <p className="mt-1">
              {initialAttribution.utm_campaign ?? initialAttribution.campaign ?? "campaign"} ·{" "}
              {initialAttribution.utm_source ?? initialAttribution.channel ?? "source"}
            </p>
          </div>
        ) : null}
        {result ? (
          <pre className="mt-5 max-h-[520px] overflow-auto rounded-2xl bg-happy-blue-900 text-cream-50 p-4 text-xs whitespace-pre-wrap">{JSON.stringify(result, null, 2)}</pre>
        ) : (
          <div className="mt-5 rounded-2xl bg-cream-100 p-4 text-sm text-ink/70">
            Submit the form to see the exact agent-readable order-intent payload, owner-gate decision, and POS/kitchen handoff hints.
          </div>
        )}
      </aside>
    </div>
  );
}
