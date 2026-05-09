import { loadCatalog, priceRange } from "@/lib/catalog";

export const metadata = { title: "Menu — HappyCake US" };

export default function Menu() {
  const catalog = loadCatalog();
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
          Order by WhatsApp or Instagram DM. Most cakes are ready in 90 minutes; cakes with hand-piped
          names need 3 hours. Pickup at our Sugar Land kitchen.
        </p>
      </header>

      {Object.entries(byCategory).map(([cat, items]) => (
        <section key={cat}>
          <h2 className="font-display text-2xl text-happy-blue-900 capitalize mb-5">
            {cat === "celebration" ? "Celebration cakes" : cat === "everyday" ? "Everyday favorites" : "Signature cakes"}
          </h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {items.map((item) => {
              const { min, max } = priceRange(item);
              return (
                <a
                  key={item.id}
                  href={`/p/${item.slug}`}
                  className="rounded-2xl bg-cream-100 p-5 hover:bg-cream-200 transition"
                >
                  <div className="aspect-[4/3] rounded-xl bg-happy-blue-200 mb-4 flex items-center justify-center text-happy-blue-700/60 text-xs">
                    {item.name}
                  </div>
                  <h3 className="font-display text-lg text-happy-blue-900">{item.name}</h3>
                  <p className="text-sm text-ink/70 mt-1 line-clamp-3">{item.description}</p>
                  <div className="mt-4 flex items-center justify-between text-sm">
                    <span className="font-medium text-happy-blue-700">${min}–${max}</span>
                    <span className="text-ink/60">{item.leadTimeMinutes ?? 90} min lead</span>
                  </div>
                </a>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
