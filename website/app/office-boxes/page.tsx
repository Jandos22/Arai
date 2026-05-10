import Image from "next/image";

const campaign = {
  landingPath: "/office-boxes",
  campaign: "office-boxes",
  campaignId: "mkt_1778367156160",
  channel: "google_local",
  utm_source: "google_local",
  utm_medium: "paid_local",
  utm_campaign: "office_boxes_sugar_land",
  utm_content: "landing_cta",
};

function orderHref(content = campaign.utm_content) {
  const params = new URLSearchParams({
    product: "medovik-honey-cake",
    landingPath: campaign.landingPath,
    campaign: campaign.campaign,
    campaignId: campaign.campaignId,
    channel: campaign.channel,
    utm_source: campaign.utm_source,
    utm_medium: campaign.utm_medium,
    utm_campaign: campaign.utm_campaign,
    utm_content: content,
  });
  return `/order?${params.toString()}`;
}

const whatsappText =
  "Hi HappyCake, I need office dessert boxes for a Sugar Land workplace. Please help me pick the right quantity.";

export const metadata = {
  title: "Office dessert boxes",
  description:
    "Office dessert boxes for Sugar Land teams, routed with campaign attribution into HappyCake's website, WhatsApp, Instagram, or owner approval paths.",
};

export default function OfficeBoxesPage() {
  const whatsappHref = `https://wa.me/12815551234?text=${encodeURIComponent(whatsappText)}`;
  const instagramHref = "https://instagram.com/happycakeus";

  return (
    <div className="space-y-14">
      <section className="grid lg:grid-cols-[1.05fr_0.95fr] gap-10 items-center pt-2">
        <div>
          <p className="uppercase tracking-widest text-xs text-happy-blue-500 font-medium">
            Sugar Land offices · Tuesday to Friday pickup
          </p>
          <h1 className="mt-4 font-display text-5xl md:text-6xl leading-tight text-happy-blue-900">
            Dessert boxes for the team table.
          </h1>
          <p className="mt-6 text-lg text-ink/80 max-w-xl">
            Medovik slices, cake truffles, and celebration cakes packed for workplace birthdays,
            client lunches, and Friday break-room rituals. Standard boxes stay self-serve; high-value
            or decorated requests go to owner review before the kitchen commits.
          </p>
          <div className="mt-8 flex gap-3 flex-wrap">
            <a
              href={orderHref()}
              className="rounded-full bg-happy-blue-700 text-cream-50 px-6 py-3 hover:bg-happy-blue-900 font-medium"
            >
              Start office order
            </a>
            <a
              href={whatsappHref}
              className="rounded-full border border-happy-blue-700 text-happy-blue-700 px-6 py-3 hover:bg-happy-blue-200/40 font-medium"
            >
              Ask on WhatsApp
            </a>
            <a
              href={instagramHref}
              className="rounded-full border border-coral text-coral px-6 py-3 hover:bg-coral/10 font-medium"
            >
              Instagram DM
            </a>
          </div>
        </div>
        <div className="relative aspect-[4/5] rounded-3xl overflow-hidden bg-cream-100 shadow-xl">
          <Image
            src="/brand/products/happy-cake-product-10.webp"
            alt="Layer cake slice prepared for sharing at an office dessert table."
            fill
            priority
            sizes="(min-width: 1024px) 44vw, 100vw"
            className="object-cover"
          />
        </div>
      </section>

      <section className="grid md:grid-cols-3 gap-6">
        <div className="rounded-2xl bg-cream-100 p-6">
          <p className="font-display text-2xl text-happy-blue-900">Website</p>
          <p className="mt-2 text-sm text-ink/75">
            Start with cake, quantity, and pickup timing when the order is straightforward.
          </p>
        </div>
        <div className="rounded-2xl bg-cream-100 p-6">
          <p className="font-display text-2xl text-happy-blue-900">WhatsApp or Instagram</p>
          <p className="mt-2 text-sm text-ink/75">
            Send a quick message when you need help matching box size to the room.
          </p>
        </div>
        <div className="rounded-2xl bg-cream-100 p-6">
          <p className="font-display text-2xl text-happy-blue-900">Owner approval</p>
          <p className="mt-2 text-sm text-ink/75">
            Larger office orders and decorated requests get a direct confirmation before we commit.
          </p>
        </div>
      </section>

      <section className="rounded-3xl bg-happy-blue-900 text-cream-50 p-8 md:p-10 flex flex-col md:flex-row md:items-center md:justify-between gap-5">
        <div>
          <p className="uppercase tracking-widest text-xs text-cream-200 font-medium">Office managers</p>
          <h2 className="font-display text-3xl mt-2">Need enough dessert for everyone?</h2>
          <p className="mt-3 text-cream-200 max-w-2xl">
            Tell us how many people are in the room, when you need pickup, and whether this is a
            birthday, client visit, or weekly team treat.
          </p>
        </div>
        <a
          href={orderHref("evidence_band")}
          className="rounded-full bg-cream-50 text-happy-blue-900 px-6 py-3 hover:bg-cream-200 font-medium text-center"
        >
          Capture attributed intent
        </a>
      </section>
    </div>
  );
}
