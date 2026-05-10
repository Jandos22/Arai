"use client";

import { useState } from "react";

type Props = {
  paymentIntentId?: string;
};

export default function MockPayButton({ paymentIntentId }: Props) {
  const [status, setStatus] = useState<"idle" | "loading" | "paid" | "error">("idle");

  async function confirm() {
    if (!paymentIntentId) {
      setStatus("error");
      return;
    }

    setStatus("loading");
    const response = await fetch("/api/payment-intent/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ paymentIntentId }),
    });
    setStatus(response.ok ? "paid" : "error");
  }

  return (
    <div>
      <button
        type="button"
        onClick={confirm}
        disabled={status === "loading" || status === "paid"}
        className="w-full rounded-full bg-happy-blue-700 px-6 py-3 font-medium text-cream-50 disabled:opacity-60"
      >
        {status === "loading" ? "Confirming..." : status === "paid" ? "Mock payment paid" : "Mock paid"}
      </button>
      {status === "paid" ? (
        <p className="mt-3 rounded-xl bg-cream-100 px-4 py-3 text-sm text-happy-blue-900">
          Payment marked paid in the mock provider. Production should use a signed Square webhook for this transition.
        </p>
      ) : null}
      {status === "error" ? (
        <p className="mt-3 rounded-xl bg-cream-100 px-4 py-3 text-sm text-coral">
          Could not confirm this mock payment intent.
        </p>
      ) : null}
    </div>
  );
}
