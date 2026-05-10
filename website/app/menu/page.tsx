import Image from "next/image";
import { itemAvailabilityLabel, loadAvailability } from "@/lib/availability";
import { loadCatalog, priceRange } from "@/lib/catalog";

export const metadata = { title: "Menu — HappyCake US" };
export const dynamic = "force-dynamic";

const CATEGORY_LABELS: Record<string, string> = {
  signature: "Signature cakes",
  celebration: "Celebration cakes",
  everyday: "Everyday favorites",
  seasonal: "Seasonal",
  "by-request": "By request",
};

function leadDisplay(min: number | undefined): string {
  if (!min) return "90 min lead";
  if (min < 60) return `${min} min lead`;
  if (min < 24 * 60) return `${Math.round(min / 60)} hr lead`;
  return `${Math.round(min / 60 / 24)}-day lead`;
}

export default async function Menu() {
  const catalog = loadCatalog();
  const availability = await loadAvailability();
  const byCategory = catalog.items.reduce<Record<string, typeof catalog.items>>((acc, item) => {
    (acc[item.category] ||= []).push(item);
    return acc;
  }, {});

  return (
    <div className="space-y-12">
      <header>
        <p className="uppercase tracking-widest text-xs text-happy-blue-500 font-medium">Menu</p>
        <h1 className="mt-2 font-display text-4xl text-happy-blue-900">Every cake, every size.</h1>
        <p className="mt-3 text-ink/70 max-w-xl">
          Order by WhatsApp or Instagram DM. Stock and kitchen capacity are checked before we confirm
          a pickup window at our Sugar Land kitchen.
        </p>
        <div className="mt-5 rounded-2xl border border-happy-blue-200 bg-white p-4 text-sm text-ink/75">
          <p className="font-medium text-happy-blue-900">Today&apos;s capacity</p>
          <p className="mt-1">{availability.customerPromise}</p>
        </div>
      </header>

      {Object.entries(byCategory).map(([cat, items]) => (
        <section key={cat}>
          <h2 className="font-display text-2xl text-happy-blue-900 mb-5">
            {CATEGORY_LABELS[cat] ?? cat}
          </h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {items.map((item) => {
              const { min, max } = priceRange(item);
              return (
                <a
                  key={item.id}
                  href={`/products/${item.slug}`}
                  className="group rounded-2xl bg-cream-100 p-5 hover:bg-cream-200 transition"
                >
                  <div className="relative aspect-[4/3] rounded-xl overflow-hidden bg-happy-blue-200 mb-4">
                    {item.imageUrl ? (
                      <Image
                        src={item.imageUrl}
                        alt={item.imageAlt ?? item.name}
                        fill
                        sizes="(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
                        className="object-cover group-hover:scale-105 transition duration-500"
                      />
                    ) : (
                      <div className="flex items-center justify-center h-full text-happy-blue-700/60 text-xs px-3 text-center">
                        {item.name} <br /> <span className="text-[10px] mt-1">photo on request</span>
                      </div>
                    )}
                  </div>
                  <h3 className="font-display text-lg text-happy-blue-900">{item.name}</h3>
                  <p className="text-sm text-ink/70 mt-1 line-clamp-3">{item.description}</p>
                  <div className="mt-4 flex items-center justify-between text-sm">
                    <span className="font-medium text-happy-blue-700">${min}–${max}</span>
                    <span className="text-ink/60">{leadDisplay(item.leadTimeMinutes)}</span>
                  </div>
                  <p className="mt-2 text-xs font-medium text-coral">
                    {itemAvailabilityLabel(availability, item)}
                  </p>
                </a>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
