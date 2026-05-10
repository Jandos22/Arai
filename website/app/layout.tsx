import "./globals.css";
import type { Metadata } from "next";

const SITE_URL = "https://happycake.us";

// LocalBusiness/Bakery JSON-LD — agent + SEO discoverability.
// Only production-confirmed public facts are emitted here. Specific phone,
// street address, and hours stay out of schema until HappyCake confirms them
// for the real happycake.us cutover (see docs/PRODUCTION-PATH.md).
const localBusinessJsonLd = {
  "@context": "https://schema.org",
  "@type": "Bakery",
  "@id": `${SITE_URL}/#org`,
  name: "HappyCake US",
  alternateName: "HappyCake",
  description:
    "Traditional, hand-decorated cakes in Sugar Land, TX. Honey cake, Napoleon, Red Velvet, and more — made by hand, sold by neighborhood reputation.",
  url: SITE_URL,
  logo: `${SITE_URL}/brand/logo/logo-512.png`,
  image: `${SITE_URL}/brand/hero/hero-04.webp`,
  priceRange: "$$",
  servesCuisine: ["Cakes", "Desserts", "Pastries"],
  address: {
    "@type": "PostalAddress",
    addressLocality: "Sugar Land",
    addressRegion: "TX",
    addressCountry: "US",
  },
  areaServed: [
    { "@type": "City", name: "Sugar Land" },
    { "@type": "City", name: "Missouri City" },
    { "@type": "City", name: "Stafford" },
    { "@type": "City", name: "Richmond" },
    { "@type": "City", name: "Houston" },
  ],
  sameAs: ["https://instagram.com/happycakeus"],
  potentialAction: {
    "@type": "OrderAction",
    target: `${SITE_URL}/order`,
    deliveryMethod: ["http://purl.org/goodrelations/v1#DeliveryModePickUp"],
  },
};

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "HappyCake US — The original taste of happiness",
    template: "%s · HappyCake US",
  },
  description:
    "Hand-decorated, hand-packed cakes in Sugar Land, TX. The traditional, time-tested cakes our customers say taste 'just like homemade'.",
  applicationName: "HappyCake US",
  authors: [{ name: "HappyCake US" }],
  keywords: [
    "Sugar Land cakes",
    "Houston bakery",
    "Medovik honey cake",
    "Napoleon cake",
    "custom birthday cake Sugar Land",
    "Russian cakes Houston",
  ],
  alternates: {
    canonical: SITE_URL,
  },
  openGraph: {
    type: "website",
    url: SITE_URL,
    siteName: "HappyCake US",
    title: "HappyCake US — The original taste of happiness",
    description:
      "Traditional, hand-decorated cakes in Sugar Land, TX. Order ahead by WhatsApp or pick up today.",
    locale: "en_US",
    images: [
      {
        url: "/brand/hero/hero-04.webp",
        width: 1600,
        height: 1000,
        alt: "Naked chocolate layer cake with piped cream pearls and ganache drip.",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "HappyCake US — The original taste of happiness",
    description: "Hand-decorated cakes in Sugar Land, TX.",
    images: ["/brand/hero/hero-04.webp"],
  },
  robots: {
    index: true,
    follow: true,
  },
  icons: {
    icon: "/brand/logo/logo-256.png",
    apple: "/brand/logo/logo-512.png",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Inter:wght@400;500;600&display=swap"
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(localBusinessJsonLd) }}
        />
      </head>
      <body className="bg-cream-50 text-ink antialiased">
        <header className="border-b border-cream-200 bg-cream-50/95 backdrop-blur sticky top-0 z-10">
          <div className="mx-auto max-w-6xl flex h-16 items-center justify-between px-6">
            <a href="/" className="font-display text-xl font-bold text-happy-blue-700">
              HappyCake <span className="text-coral">·</span> US
            </a>
            <nav className="flex gap-5 text-sm items-center">
              <a href="/menu" className="hover:text-happy-blue-500">Menu</a>
              <a href="/assistant" className="hover:text-happy-blue-500">Assistant</a>
              <a href="/order" className="hover:text-happy-blue-500">Order</a>
              <a href="/policies" className="hover:text-happy-blue-500">Policies</a>
              <a
                href="https://wa.me/12815551234?text=Hi%20HappyCake%2C%20I%27d%20like%20to%20ask%20about%20a%20cake."
                className="rounded-full bg-happy-blue-700 text-cream-50 px-4 py-1.5 hover:bg-happy-blue-900"
              >
                WhatsApp us
              </a>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-10">{children}</main>
        <footer className="border-t border-cream-200 mt-16 py-10 text-sm text-ink/70">
          <div className="mx-auto max-w-6xl px-6 grid md:grid-cols-3 gap-6">
            <div>
              <p className="font-display text-lg text-happy-blue-700">HappyCake US</p>
              <p className="mt-2">Sugar Land, TX · Houston metro</p>
              <p>The original taste of happiness.</p>
            </div>
            <div>
              <p className="font-medium">Order</p>
              <ul className="mt-2 space-y-1">
                <li><a href="/menu" className="hover:text-happy-blue-500">Menu</a></li>
                <li><a href="/order" className="hover:text-happy-blue-500">Website order intent</a></li>
                <li><a href="/assistant" className="hover:text-happy-blue-500">On-site assistant</a></li>
                <li><a href="https://wa.me/12815551234" className="hover:text-happy-blue-500">WhatsApp</a></li>
                <li><a href="https://instagram.com/happycakeus" className="hover:text-happy-blue-500">Instagram DM</a></li>
              </ul>
            </div>
            <div>
              <p className="font-medium">For agents</p>
              <ul className="mt-2 space-y-1">
                <li><a href="/agent.json" className="hover:text-happy-blue-500">/agent.json</a></li>
                <li><a href="/api/catalog" className="hover:text-happy-blue-500">/api/catalog</a></li>
                <li><a href="/api/policies" className="hover:text-happy-blue-500">/api/policies</a></li>
                <li><a href="/api/assistant" className="hover:text-happy-blue-500">/api/assistant</a></li>
                <li><a href="/api/order-intent" className="hover:text-happy-blue-500">/api/order-intent</a></li>
                <li><a href="/sitemap.xml" className="hover:text-happy-blue-500">/sitemap.xml</a></li>
              </ul>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
