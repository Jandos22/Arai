import Image from "next/image";
import { loadAvailability } from "@/lib/availability";
import { loadCatalog, priceRange } from "@/lib/catalog";
import PretextEnhancer from "./PretextEnhancer";

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
  const inventoryLive = availability.tools.square_get_inventory === "live";

  return (
    <div className="space-y-20">
      <PretextEnhancer />

      {/* ── HERO ──────────────────────────────────── */}
      <section className="grid md:grid-cols-[1.2fr_0.8fr] gap-10 md:gap-14 items-center pt-2">
        <div>
          <p className="uppercase tracking-widest text-xs text-happy-blue-500 font-medium">
            Sugar Land, TX <span className="text-cream-200 mx-2">◆</span> Hand-baked daily
          </p>
          <h1
            data-pretext
            className="mt-4 font-display text-5xl md:text-6xl leading-[1.04] tracking-tight text-happy-blue-900 font-medium"
            style={{ fontVariationSettings: '"opsz" 96, "SOFT" 60, "WONK" 0' }}
          >
            The original taste of{" "}
            <span
              className="text-coral italic"
              style={{ fontVariationSettings: '"opsz" 96, "SOFT" 100, "WONK" 1' }}
            >
              happiness
            </span>
            .
          </h1>
          <p data-pretext className="mt-6 text-lg leading-snug text-ink/80 max-w-md">
            Traditional, time-tested cakes — hand-decorated, hand-packed, the kind your grandmother
            would say tastes like real home baking. Order ahead by WhatsApp or request a confirmed
            pickup window.
          </p>
          <div className="mt-8 flex gap-3 flex-wrap">
            <a
              href="/menu"
              className="rounded-full bg-happy-blue-700 text-cream-50 px-6 py-3 hover:bg-happy-blue-900 font-medium transition"
            >
              See the cakes
            </a>
            <a
              href="/order"
              className="rounded-full border border-happy-blue-700 text-happy-blue-700 px-6 py-3 hover:bg-happy-blue-200/40 font-medium transition"
            >
              Start website order
            </a>
            <a
              href="/assistant"
              className="rounded-full border border-coral text-coral px-6 py-3 hover:bg-coral/10 font-medium transition"
            >
              Ask cake assistant
            </a>
          </div>
        </div>
        <div className="relative aspect-[4/5] rounded-3xl overflow-hidden bg-cream-100 ring-1 ring-happy-blue-900/5">
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

      {/* ── AVAILABILITY STRIP ────────────────────── */}
      <section className="rounded-2xl border border-happy-blue-200 bg-white p-6 md:p-7">
        <div className="grid gap-5 md:grid-cols-[1.2fr_0.8fr] md:items-center md:gap-7">
          <div>
            <p className="uppercase tracking-widest text-xs text-happy-blue-500 font-medium">
              Today, in the kitchen
            </p>
            <h2
              data-pretext
              className="mt-2 font-display text-2xl md:text-[26px] leading-tight tracking-tight text-happy-blue-900 font-medium"
            >
              Stock and pickup timing are checked before we promise.
            </h2>
            <p data-pretext className="mt-3 text-sm text-ink/75 max-w-2xl leading-relaxed">
              {availability.customerPromise}
            </p>
          </div>
          <div className="grid gap-3 text-sm">
            <div className="rounded-xl bg-cream-100 px-4 py-3">
              <p className="font-medium text-happy-blue-900">Inventory</p>
              <p className="text-ink/70 mt-0.5 flex items-center gap-2">
                <span
                  aria-hidden
                  className={`inline-block w-2 h-2 rounded-full ${
                    inventoryLive ? "bg-leaf" : "bg-coral"
                  }`}
                />
                {inventoryLive
                  ? "Live Square inventory connected."
                  : "Live Square inventory unavailable; stock needs confirmation."}
              </p>
            </div>
            <div className="rounded-xl bg-cream-100 px-4 py-3">
              <p className="font-medium text-happy-blue-900">Kitchen capacity</p>
              <p className="text-ink/70 mt-0.5">{availability.capacity.label}</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── TODAY'S CAKES ─────────────────────────── */}
      <section>
        <div className="flex items-end justify-between mb-7 gap-4">
          <h2 className="font-display text-3xl md:text-[36px] leading-[1.08] tracking-tight text-happy-blue-900 font-medium">
            Today&rsquo;s cakes
          </h2>
          <a href="/menu" className="text-sm text-happy-blue-500 hover:text-happy-blue-900 whitespace-nowrap">
            See full menu →
          </a>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5 lg:gap-5">
          {featured.map((item) => {
            const { min, max } = priceRange(item);
            const lead = item.leadTimeMinutes
              ? item.leadTimeMinutes >= 60
                ? `${Math.round(item.leadTimeMinutes / 60)} hr`
                : `${item.leadTimeMinutes} min`
              : null;
            return (
              <a
                key={item.id}
                href={`/products/${item.slug}`}
                className="group rounded-2xl bg-cream-100 p-4 hover:bg-cream-200 transition"
              >
                <div className="relative aspect-square rounded-xl overflow-hidden bg-happy-blue-200 mb-4">
                  {item.imageUrl ? (
                    <Image
                      src={homeImageByUrl[item.imageUrl] ?? item.imageUrl}
                      alt={item.imageAlt ?? item.name}
                      fill
                      sizes="(min-width: 1024px) 25vw, (min-width: 640px) 50vw, 100vw"
                      className="object-cover group-hover:scale-[1.04] transition duration-500"
                    />
                  ) : (
                    <div className="flex items-center justify-center h-full text-happy-blue-700/60 text-xs">
                      {item.name}
                    </div>
                  )}
                </div>
                <h3
                  data-pretext
                  className="font-display text-lg leading-tight tracking-tight text-happy-blue-900 font-medium"
                >
                  {item.name}
                </h3>
                <p
                  data-pretext
                  className="text-sm text-ink/70 mt-1.5 leading-snug"
                >
                  {item.description}
                </p>
                <div className="mt-3 flex items-center justify-between text-sm">
                  <span className="font-medium text-happy-blue-700">
                    ${min}–${max}
                  </span>
                  {lead && (
                    <span className="rounded-full bg-cream-50 px-2.5 py-0.5 text-[11px] text-ink/60">
                      {lead}
                    </span>
                  )}
                </div>
              </a>
            );
          })}
        </div>
      </section>

      {/* ── EDITORIAL ─────────────────────────────── */}
      <section className="grid md:grid-cols-[0.9fr_1.1fr] gap-10 md:gap-14 items-center">
        <div className="relative aspect-[4/5] rounded-3xl overflow-hidden bg-cream-100">
          <Image
            src="/brand/home/happy-cake-product-09-720.webp"
            alt="Pastel buttercream layer cake on a cream surface, soft natural light."
            fill
            sizes="(min-width: 768px) 40vw, 100vw"
            className="object-cover"
          />
        </div>
        <div>
          <p className="uppercase tracking-widest text-xs text-happy-blue-500 font-medium">
            A note from the kitchen
          </p>
          <p
            data-pretext
            className="mt-3 font-display text-3xl md:text-[40px] leading-[1.12] tracking-tight text-happy-blue-900"
            style={{ fontVariationSettings: '"opsz" 72, "SOFT" 60, "WONK" 1' }}
          >
            Tastes like{" "}
            <em className="text-coral italic">real home baking</em> — the cakes our
            grandmothers actually made.
          </p>

          <div className="mt-9 grid gap-7">
            {[
              {
                num: "01",
                title: "Real ingredients only",
                body:
                  "Butter, eggs, flour, sour cream, honey. Recipes our team has tuned for years. No shortcuts — and no added flavour numbers we can't pronounce.",
              },
              {
                num: "02",
                title: "Hand-decorated, every time",
                body:
                  "Every cake is finished by a person who actually loves cake. No printer transfers, no piped templates. Each one looks slightly different — that's the point.",
              },
              {
                num: "03",
                title: "Confirmed pickup, never promised early",
                body:
                  'Same-day pickup is requested when stock and kitchen capacity allow; every pickup window is confirmed first. We’d rather say "tomorrow at four" than miss a Saturday evening.',
              },
            ].map((row) => (
              <div key={row.num} className="grid sm:grid-cols-[96px_1fr] gap-2 sm:gap-5 items-start">
                <span className="hidden sm:block font-display text-[38px] leading-none text-happy-blue-500 border-t border-cream-200 pt-3.5 tracking-tight">
                  {row.num}
                </span>
                <div className="sm:border-t sm:border-cream-200 sm:pt-3.5">
                  <h3 className="font-display text-lg text-happy-blue-900 font-medium leading-tight">
                    {row.title}
                  </h3>
                  <p data-pretext className="mt-1.5 text-[15px] text-ink/75 leading-snug">
                    {row.body}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── TRUST STRIP ───────────────────────────── */}
      <section className="rounded-3xl bg-happy-blue-900 text-cream-50 p-10 md:p-12 grid md:grid-cols-3 gap-8">
        <div>
          <p className="uppercase tracking-widest text-xs text-cream-200/80 mb-2">By hand</p>
          <p className="font-display text-2xl leading-tight">Hand-decorated.</p>
          <p className="text-cream-200/80 mt-2.5 text-sm leading-relaxed">
            Every cake is finished by a person who actually loves cake.
          </p>
        </div>
        <div>
          <p className="uppercase tracking-widest text-xs text-cream-200/80 mb-2">When you need it</p>
          <p className="font-display text-2xl leading-tight">Same-day pickup.</p>
          <p className="text-cream-200/80 mt-2.5 text-sm leading-relaxed">
            Requested when stock and kitchen capacity allow; every pickup window is confirmed first.
          </p>
        </div>
        <div>
          <p className="uppercase tracking-widest text-xs text-cream-200/80 mb-2">Pantry, not lab</p>
          <p className="font-display text-2xl leading-tight">Real ingredients.</p>
          <p className="text-cream-200/80 mt-2.5 text-sm leading-relaxed">
            Butter, eggs, flour, sour cream, honey. Recipes our team has tuned for years.
          </p>
        </div>
      </section>
    </div>
  );
}
