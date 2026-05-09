import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "HappyCake US — The original taste of happiness",
  description:
    "Hand-decorated, hand-packed cakes in Sugar Land, TX. The traditional, time-tested cakes our customers say taste 'just like homemade'.",
  metadataBase: new URL("https://happycake.us"),
  openGraph: {
    title: "HappyCake US",
    description: "The original taste of happiness — Sugar Land, TX.",
    type: "website",
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
      </head>
      <body className="bg-cream-50 text-ink antialiased">
        <header className="border-b border-cream-200 bg-cream-50/95 backdrop-blur sticky top-0 z-10">
          <div className="mx-auto max-w-6xl flex h-16 items-center justify-between px-6">
            <a href="/" className="font-display text-xl font-bold text-happy-blue-700">
              HappyCake <span className="text-coral">·</span> US
            </a>
            <nav className="flex gap-6 text-sm">
              <a href="/menu" className="hover:text-happy-blue-500">Menu</a>
              <a href="/about" className="hover:text-happy-blue-500">About</a>
              <a href="/policies" className="hover:text-happy-blue-500">Pickup &amp; policies</a>
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
              </ul>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
