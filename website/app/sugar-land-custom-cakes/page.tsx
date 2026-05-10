import type { Metadata } from "next";

const SITE_URL = "https://happycake.us";
const PAGE_URL = `${SITE_URL}/sugar-land-custom-cakes`;

export const metadata: Metadata = {
  title: "Sugar Land custom cakes & birthday cakes",
  description:
    "Hand-decorated honey cake (medovik), Napoleon, Red Velvet, and birthday cakes baked in Sugar Land, TX. Pickup ready by neighbourhood reputation — order on the site or send a WhatsApp message.",
  alternates: { canonical: PAGE_URL },
  openGraph: {
    title: "Sugar Land custom cakes — HappyCake US",
    description:
      "Sugar Land neighbourhood bakery. Honey cake, Napoleon, Red Velvet, custom birthday cake. Pickup-first, with limited local delivery on case-by-case quote.",
    url: PAGE_URL,
  },
};

const serviceJsonLd = {
  "@context": "https://schema.org",
  "@type": "Service",
  serviceType: "Custom and ready-made cake baking",
  provider: { "@id": `${SITE_URL}/#org` },
  areaServed: [
    { "@type": "City", name: "Sugar Land" },
    { "@type": "City", name: "Missouri City" },
    { "@type": "City", name: "Stafford" },
    { "@type": "City", name: "Richmond" },
    { "@type": "City", name: "Houston" },
  ],
  hasOfferCatalog: {
    "@type": "OfferCatalog",
    name: "HappyCake Sugar Land cake line",
    itemListElement: [
      { "@type": "Offer", name: "Cake \"Honey\" (medovik)" },
      { "@type": "Offer", name: "Cake \"Napoleon\"" },
      { "@type": "Offer", name: "Cake \"Red Velvet\"" },
      { "@type": "Offer", name: "Custom birthday cake (owner-reviewed)" },
      { "@type": "Offer", name: "Office dessert box" },
    ],
  },
  url: PAGE_URL,
};

const faqJsonLd = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: [
    {
      "@type": "Question",
      name: "Do you make custom birthday cakes in Sugar Land?",
      acceptedAnswer: {
        "@type": "Answer",
        text:
          "Yes. We're a ready-made bakery first, and we add custom decoration on request. A piped first name on cake \"Honey\" or cake \"Red Velvet\" is standard. Larger custom work (sculpted toppers, multi-tier, photo prints) is owner-reviewed before we promise capacity.",
      },
    },
    {
      "@type": "Question",
      name: "Can I pick up the same day?",
      acceptedAnswer: {
        "@type": "Answer",
        text:
          "Honey cake slices are usually same-day. Whole cakes need 60–120 minutes lead time depending on the cake. The custom birthday cake needs 24 hours. We never confirm same-day pickup without checking inventory and kitchen capacity first.",
      },
    },
    {
      "@type": "Question",
      name: "Do you deliver in Sugar Land?",
      acceptedAnswer: {
        "@type": "Answer",
        text:
          "Pickup is the default. We quote local delivery case-by-case on larger orders inside Sugar Land, Missouri City, Stafford, Richmond, and parts of Houston. Send a WhatsApp message with your address and we'll confirm.",
      },
    },
    {
      "@type": "Question",
      name: "Are your cakes safe for nut or dairy allergies?",
      acceptedAnswer: {
        "@type": "Answer",
        text:
          "Traditional cakes like cake \"Honey\" (medovik) contain wheat, egg, and dairy, and may contain traces of nuts or soy. We don't promise allergen safety on this kitchen. Always tell us about allergies before ordering — for serious allergies, the owner reviews the order before we accept.",
      },
    },
  ],
};

export default function SugarLandCakes() {
  return (
    <div className="prose prose-stone max-w-3xl">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(serviceJsonLd) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
      />
      <p className="uppercase tracking-widest text-xs text-happy-blue-500 font-medium">
        Sugar Land
      </p>
      <h1 className="font-display text-4xl text-happy-blue-900 mt-2">
        Sugar Land custom cakes & traditional bakes
      </h1>
      <p className="text-lg text-happy-blue-700">
        Hand-decorated, hand-packed, made in our Sugar Land kitchen.
      </p>

      <p>
        HappyCake is a Sugar Land neighbourhood bakery. We bake the
        traditional cakes our customers say taste &ldquo;just like
        homemade&rdquo; — cake &ldquo;Honey&rdquo; (medovik), cake
        &ldquo;Napoleon&rdquo;, cake &ldquo;Red Velvet&rdquo;, and a small line
        of seasonal celebration cakes. Pickup is the default; local delivery
        is quoted case-by-case for larger orders inside Sugar Land, Missouri
        City, Stafford, Richmond, and Houston.
      </p>

      <h2>What we&rsquo;re known for in Sugar Land</h2>
      <ul>
        <li>
          <strong>Cake &ldquo;Honey&rdquo; (medovik).</strong> Eight thin
          honey-baked layers, sour-cream filling, golden crumb top. Our
          signature.
        </li>
        <li>
          <strong>Cake &ldquo;Napoleon&rdquo;.</strong> Flaky butter pastry,
          custard cream. The fond-memories cake.
        </li>
        <li>
          <strong>Custom birthday cake.</strong> Piped first name and a candle
          set are standard. Larger themed designs are owner-reviewed before we
          promise a date.
        </li>
        <li>
          <strong>Office dessert box.</strong> Mixed slices for 8&ndash;12
          people. Lead time 3 hours.
        </li>
      </ul>

      <h2>Frequently asked</h2>
      <h3>Do you make custom birthday cakes?</h3>
      <p>
        Yes. A piped first name on cake &ldquo;Honey&rdquo; or cake &ldquo;Red
        Velvet&rdquo; is our standard celebration finish. Larger custom work
        (sculpted toppers, multi-tier, photo prints) is owner-reviewed before
        we promise kitchen capacity.
      </p>
      <h3>Can I pick up the same day?</h3>
      <p>
        Honey cake slices are usually same-day. Whole cakes need 60&ndash;120
        minutes lead time. The custom birthday cake needs 24 hours. We
        won&rsquo;t confirm same-day pickup without checking inventory and
        kitchen capacity.
      </p>
      <h3>Do you deliver in Sugar Land?</h3>
      <p>
        Pickup is the default. We quote local delivery case-by-case on larger
        orders. Send a WhatsApp message with your address and we&rsquo;ll
        confirm.
      </p>
      <h3>Are your cakes allergen-safe?</h3>
      <p>
        Traditional cakes contain wheat, egg, and dairy, and may contain
        traces of nuts or soy. We don&rsquo;t promise allergen safety. Always
        tell us about allergies before ordering — for serious allergies, the
        owner reviews the order first.
      </p>

      <h2>Order</h2>
      <p>
        Order on the site at <a href="/order">happycake.us/order</a> or send a
        message on{" "}
        <a href="https://wa.me/12819798320">WhatsApp</a>. Our menu is at{" "}
        <a href="/menu">happycake.us/menu</a>.
      </p>
    </div>
  );
}
