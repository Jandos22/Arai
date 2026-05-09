import Image from "next/image";
import { findBySlug, loadCatalog } from "@/lib/catalog";
import { notFound } from "next/navigation";

export function generateStaticParams() {
  return loadCatalog().items.map((i) => ({ slug: i.slug }));
}

export default async function ProductPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const item = findBySlug(slug);
  if (!item) notFound();

  const minPrice = Math.min(...item.variations.map((v) => v.priceUsd));
  const maxPrice = Math.max(...item.variations.map((v) => v.priceUsd));

  // JSON-LD Product schema for agent-readable product data
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: item.name,
    description: item.description,
    image: item.imageUrl ? `https://happycake.us${item.imageUrl}` : undefined,
    brand: { "@type": "Brand", name: "HappyCake US" },
    category: item.category,
    offers: item.variations.map((v) => ({
      "@type": "Offer",
      sku: v.id,
      name: v.name,
      price: v.priceUsd,
      priceCurrency: "USD",
      availability: v.available
        ? "https://schema.org/InStock"
        : "https://schema.org/OutOfStock",
      itemCondition: "https://schema.org/NewCondition",
      seller: { "@type": "Organization", name: "HappyCake US" },
    })),
    additionalProperty: [
      ...(item.leadTimeMinutes
        ? [{ "@type": "PropertyValue", name: "leadTimeMinutes", value: item.leadTimeMinutes }]
        : []),
      ...(item.allergens
        ? [{ "@type": "PropertyValue", name: "allergens", value: item.allergens.join(", ") }]
        : []),
    ],
  };

  const waUrl = `https://wa.me/12815551234?text=${encodeURIComponent(
    `Hi HappyCake! I'd like to order: ${item.name}.`
  )}`;

  return (
    <article className="grid md:grid-cols-2 gap-10">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <div className="relative aspect-square rounded-3xl overflow-hidden bg-cream-100 shadow-md">
        {item.imageUrl ? (
          <Image
            src={item.imageUrl}
            alt={item.imageAlt ?? item.name}
            fill
            priority
            sizes="(min-width: 768px) 50vw, 100vw"
            className="object-cover"
          />
        ) : (
          <div className="flex items-center justify-center h-full text-happy-blue-700/70 font-display text-2xl text-center px-6">
            {item.name}
          </div>
        )}
      </div>
      <div>
        <p className="uppercase tracking-widest text-xs text-happy-blue-500 font-medium">
          {item.category}
        </p>
        <h1 className="mt-2 font-display text-4xl text-happy-blue-900">{item.name}</h1>
        <p className="mt-2 text-happy-blue-700 font-medium text-lg">
          ${minPrice}–${maxPrice}
        </p>
        <p className="mt-6 text-ink/80 leading-relaxed">{item.description}</p>

        <h2 className="font-display text-xl text-happy-blue-900 mt-8 mb-3">Sizes</h2>
        <ul className="space-y-2">
          {item.variations.map((v) => (
            <li
              key={v.id}
              className="flex items-center justify-between rounded-xl bg-cream-100 px-4 py-3"
            >
              <span>{v.name}</span>
              <span className="font-medium">${v.priceUsd}</span>
            </li>
          ))}
        </ul>

        {(item.leadTimeMinutes || item.allergens?.length) && (
          <div className="mt-6 text-sm text-ink/70 space-y-1">
            {item.leadTimeMinutes && (
              <p>
                <strong className="text-ink">Lead time:</strong> {item.leadTimeMinutes} minutes
                from order to ready.
              </p>
            )}
            {item.allergens?.length && (
              <p>
                <strong className="text-ink">Contains:</strong> {item.allergens.join(", ")}.
              </p>
            )}
          </div>
        )}

        <a
          href={waUrl}
          className="mt-8 inline-block rounded-full bg-happy-blue-700 text-cream-50 px-6 py-3 hover:bg-happy-blue-900 font-medium"
        >
          Order on WhatsApp
        </a>
      </div>
    </article>
  );
}
