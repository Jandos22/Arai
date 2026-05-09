import { loadCatalog, priceRange } from "@/lib/catalog";

export default function Home() {
  const catalog = loadCatalog();
  const featured = catalog.items.slice(0, 4);

  return (
    <div className="space-y-16">
      {/* Hero */}
      <section className="grid md:grid-cols-2 gap-10 items-center pt-6">
        <div>
          <p className="uppercase tracking-widest text-xs text-happy-blue-500 font-medium">
            Sugar Land, TX · Hand-baked daily
          </p>
          <h1 className="mt-4 font-display text-5xl md:text-6xl leading-tight text-happy-blue-900">
            The original taste of <span className="text-coral">happiness</span>.
          </h1>
          <p className="mt-6 text-lg text-ink/80 max-w-md">
            Traditional, time-tested cakes — hand-decorated, hand-packed, the kind your grandmother
            would say tastes like real home baking. Order ahead by WhatsApp or pick up today.
          </p>
          <div className="mt-8 flex gap-3 flex-wrap">
            <a
              href="/menu"
              className="rounded-full bg-happy-blue-700 text-cream-50 px-6 py-3 hover:bg-happy-blue-900 font-medium"
            >
              See the cakes
            </a>
            <a
              href="https://wa.me/12815551234?text=Hi%20HappyCake%21%20I%27d%20like%20to%20order."
              className="rounded-full border border-happy-blue-700 text-happy-blue-700 px-6 py-3 hover:bg-happy-blue-200/40 font-medium"
            >
              Order on WhatsApp
            </a>
          </div>
        </div>
        <div className="aspect-[4/5] rounded-3xl bg-gradient-to-br from-happy-blue-200 via-cream-100 to-cream-200 flex items-center justify-center">
          <div className="text-center text-happy-blue-700/70">
            <p className="font-display text-2xl">Cake photo</p>
            <p className="text-xs mt-1">Replace with brand-pack image</p>
          </div>
        </div>
      </section>

      {/* Featured cakes */}
      <section>
        <div className="flex items-end justify-between mb-6">
          <h2 className="font-display text-3xl text-happy-blue-900">Today's cakes</h2>
          <a href="/menu" className="text-sm text-happy-blue-500 hover:underline">
            See full menu →
          </a>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {featured.map((item) => {
            const { min, max } = priceRange(item);
            return (
              <a
                key={item.id}
                href={`/p/${item.slug}`}
                className="group rounded-2xl bg-cream-100 p-4 hover:bg-cream-200 transition"
              >
                <div className="aspect-square rounded-xl bg-happy-blue-200 mb-4 flex items-center justify-center text-happy-blue-700/60 text-xs">
                  {item.name}
                </div>
                <h3 className="font-display text-lg text-happy-blue-900">{item.name}</h3>
                <p className="text-sm text-ink/70 mt-1 line-clamp-2">{item.description}</p>
                <p className="mt-3 text-sm font-medium text-happy-blue-700">
                  ${min}–${max}
                </p>
              </a>
            );
          })}
        </div>
      </section>

      {/* Trust strip */}
      <section className="rounded-3xl bg-happy-blue-900 text-cream-50 p-10 grid md:grid-cols-3 gap-8">
        <div>
          <p className="font-display text-2xl">Hand-decorated.</p>
          <p className="text-cream-200 mt-2 text-sm">
            Every cake is finished by a person who actually loves cake.
          </p>
        </div>
        <div>
          <p className="font-display text-2xl">Same-day pickup.</p>
          <p className="text-cream-200 mt-2 text-sm">
            Most cakes ready in 90 minutes from order. Custom names, 3 hours.
          </p>
        </div>
        <div>
          <p className="font-display text-2xl">Real ingredients.</p>
          <p className="text-cream-200 mt-2 text-sm">
            Butter, eggs, flour, sour cream, honey. Recipes our team has tuned for years.
          </p>
        </div>
      </section>
    </div>
  );
}
