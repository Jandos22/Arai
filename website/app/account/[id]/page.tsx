import Link from "next/link";
import { notFound } from "next/navigation";
import { loadCustomerProfile, maskPaymentToken } from "@/lib/customers";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Your Happy Cake account",
  description:
    "See your saved details, last orders, and reorder your usual in one tap. Sandbox demo — no real payment data.",
};

export default async function AccountPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const decoded = decodeURIComponent(id);
  const profile = await loadCustomerProfile(decoded);
  if (!profile) notFound();

  const fav = profile.favoriteProduct;
  const reorderHref = fav
    ? `/order?product=${encodeURIComponent(fav.sku)}&customer=${encodeURIComponent(profile.id)}&channel=quick-reorder`
    : null;

  return (
    <div className="max-w-2xl mx-auto py-12 space-y-10">
      <header className="space-y-2">
        <p className="uppercase tracking-widest text-xs text-happy-blue-500 font-medium">
          Welcome back{profile.name ? `, ${profile.name}` : ""}
        </p>
        <h1 className="font-display text-4xl text-happy-blue-900">
          Your Happy Cake account
        </h1>
        <p className="text-ink/70 text-sm">
          We auto-saved your details when you messaged us — no signup
          needed. Update anything by replying on WhatsApp or Instagram.
        </p>
      </header>

      {fav && reorderHref ? (
        <section className="rounded-2xl border border-happy-blue-200 bg-happy-blue-50 p-6 space-y-4">
          <h2 className="font-display text-xl text-happy-blue-900">
            Your usual: {fav.sku.replace(/[-_]/g, " ")}
          </h2>
          <p className="text-ink/80 text-sm">
            You&apos;ve ordered this {fav.count} time{fav.count === 1 ? "" : "s"}.
            Want it again?
          </p>
          <Link
            href={reorderHref}
            className="inline-block rounded-full bg-coral text-white px-5 py-2.5 text-sm font-medium hover:opacity-90"
          >
            Reorder in one tap
          </Link>
        </section>
      ) : (
        <section className="rounded-2xl border border-ink/10 p-6">
          <h2 className="font-display text-xl text-happy-blue-900">
            Order something to unlock quick reorder
          </h2>
          <p className="text-ink/70 text-sm mt-2">
            After your second order of the same item, we&apos;ll show a
            one-tap reorder here and on WhatsApp.
          </p>
        </section>
      )}

      <section className="grid sm:grid-cols-2 gap-4">
        <Detail label="Saved delivery address" value={profile.deliveryAddress ?? "Not saved"} />
        <Detail
          label="Saved payment"
          value={maskPaymentToken(profile.paymentToken)}
          note={profile.paymentToken ? "Sandbox demo — no real card on file." : undefined}
        />
        <Detail
          label="Channels we know you on"
          value={
            profile.channelKeys
              ? Object.entries(profile.channelKeys)
                  .map(([c, k]) => `${c}: ${k}`)
                  .join(" · ")
              : "—"
          }
        />
        <Detail label="Last seen" value={profile.lastSeen ?? "—"} />
      </section>

      <section>
        <h2 className="font-display text-xl text-happy-blue-900 mb-3">
          Last orders
        </h2>
        {profile.lastOrders && profile.lastOrders.length > 0 ? (
          <ul className="space-y-2">
            {profile.lastOrders.map((order) => (
              <li
                key={order.id}
                className="flex justify-between rounded-lg border border-ink/10 px-4 py-2 text-sm"
              >
                <span className="font-mono text-ink/70">{order.id}</span>
                <span>{order.sku.replace(/[-_]/g, " ")}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-ink/60 text-sm">No orders yet.</p>
        )}
      </section>

      <footer className="text-xs text-ink/50 border-t border-ink/10 pt-6">
        Sandbox demo. Data lives in <code>evidence/customers.json</code> and
        is recreated by orchestrator runs. Real payment integration is wired
        up post-hackathon — see <code>docs/PRODUCTION-PATH.md</code>.
      </footer>
    </div>
  );
}

function Detail({
  label,
  value,
  note,
}: {
  label: string;
  value: string;
  note?: string;
}) {
  return (
    <div className="rounded-lg border border-ink/10 p-4">
      <p className="text-[11px] uppercase tracking-widest text-ink/50">{label}</p>
      <p className="mt-1 text-sm text-ink">{value}</p>
      {note ? <p className="text-[11px] text-ink/50 mt-1">{note}</p> : null}
    </div>
  );
}
