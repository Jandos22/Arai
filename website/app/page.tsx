import Image from "next/image";
import { loadAvailability } from "@/lib/availability";
import { loadCatalog, priceRange } from "@/lib/catalog";

export const dynamic = "force-dynamic";

export default async function Home() {
  const catalog = loadCatalog();
  const availability = await loadAvailability();
  const featured = catalog.items.filter((i) => i.imageUrl).slice(0, 4);
  const homeImageByUrl: Record<string, string> = {
    "/brand/hero/happy-cake-hero-04.webp": "/brand/home/happy-cake-hero-04-900.webp",
    "/brand/products/happy-cake-product-10.webp": "/brand/home/happy-cake-product-10-720.webp",
    "/brand/products/happy-cake-product-03.webp": "/brand/home/happy-cake-product-03-720.webp",
    "/brand/products/happy-cake-product-04.webp": "/brand/home/happy-cake-product-04-720.webp",
    "/brand/products/happy-cake-product-09.webp": "/brand/home/happy-cake-product-09-720.webp",
  };

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
            would say tastes like real home baking. Order ahead by WhatsApp or request a confirmed
            pickup window.
          </p>
          <div className="mt-8 flex gap-3 flex-wrap">
            <a
              href="/menu"
              className="rounded-full bg-happy-blue-700 text-cream-50 px-6 py-3 hover:bg-happy-blue-900 font-medium"
            >
              See the cakes
            </a>
            <a
              href="/order"
              className="rounded-full border border-happy-blue-700 text-happy-blue-700 px-6 py-3 hover:bg-happy-blue-200/40 font-medium"
            >
              Start website order
            </a>
            <a
              href="/assistant"
              className="rounded-full border border-coral text-coral px-6 py-3 hover:bg-coral/10 font-medium"
            >
              Ask cake assistant
            </a>
          </div>
        </div>
        <div className="relative aspect-[4/5] rounded-3xl overflow-hidden bg-cream-100 shadow-xl">
          <Image
            src={homeImageByUrl["/brand/hero/happy-cake-hero-04.webp"]}
            alt="Naked chocolate layer cake with piped cream pearls, ganache drip, and gold-accented chocolate decor."
            fill
            priority
            sizes="(min-width: 768px) 50vw, 100vw"
            className="object-cover"
          />
        </div>
      </section>

      <section className="rounded-2xl border border-happy-blue-200 bg-white p-6">
        <div className="grid gap-5 md:grid-cols-[1.2fr_0.8fr] md:items-center">
          <div>
            <p className="uppercase tracking-widest text-xs text-happy-blue-500 font-medium">
              Availability today
            </p>
            <h2 className="mt-2 font-display text-2xl text-happy-blue-900">
              Stock and pickup timing are checked before we promise.
            </h2>
            <p className="mt-3 text-sm text-ink/75 max-w-2xl">{availability.customerPromise}</p>
          </div>
          <div className="grid gap-3 text-sm">
            <div className="rounded-xl bg-cream-100 px-4 py-3">
              <p className="font-medium text-happy-blue-900">Inventory</p>
              <p className="text-ink/70">
                {availability.tools.square_get_inventory === "live"
                  ? "Live Square inventory is connected."
                  : "Live Square inventory is unavailable; stock needs confirmation."}
              </p>
            </div>
            <div className="rounded-xl bg-cream-100 px-4 py-3">
              <p className="font-medium text-happy-blue-900">Kitchen capacity</p>
              <p className="text-ink/70">{availability.capacity.label}</p>
            </div>
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
                <div className="relative aspect-square rounded-xl overflow-hidden bg-happy-blue-200 mb-4">
                  {item.imageUrl ? (
                    <Image
                      src={homeImageByUrl[item.imageUrl] ?? item.imageUrl}
                      alt={item.imageAlt ?? item.name}
                      fill
                      sizes="(min-width: 1024px) 25vw, (min-width: 640px) 50vw, 100vw"
                      className="object-cover group-hover:scale-105 transition duration-500"
                    />
                  ) : (
                    <div className="flex items-center justify-center h-full text-happy-blue-700/60 text-xs">
                      {item.name}
                    </div>
                  )}
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
            Requested when stock and kitchen capacity allow; every pickup window is confirmed first.
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
