import type { Metadata } from "next";

const SITE_URL = "https://happycake.us";
const PAGE_URL = `${SITE_URL}/happy-path`;

export const metadata: Metadata = {
  title: "Happy Path — HappyCake truck weekly route",
  description:
    "Weekday food-truck stops across Richmond, Fulshear, Katy, Cypress, and The Woodlands. Be there 3:00–7:00 PM and grab a cake on the way home.",
  alternates: { canonical: PAGE_URL },
  openGraph: {
    title: "Happy Path — HappyCake truck weekly route",
    description:
      "The HappyCake truck on the road, Mon–Fri, 3:00–7:00 PM. Find your neighbourhood and the cake of the day.",
    url: PAGE_URL,
  },
};

type Stop = {
  weekday: "Mon" | "Tue" | "Wed" | "Thu" | "Fri";
  weekdayFull: string;
  neighborhood: string;
  city: string;
  lat: number;
  lng: number;
  heroCopy: string;
};

// Aspirational metro-wide route. This is a wider reach than the deterministic
// customer-cluster route in evidence/food-truck-route-sample.json (which stays
// inside Sugar Land / Pearland / Missouri City) — Happy Path goes one ring out
// to neighbouring cities, one stop per weekday.
const STOPS: Stop[] = [
  {
    weekday: "Mon",
    weekdayFull: "Monday",
    neighborhood: "Richmond",
    city: "Richmond",
    lat: 29.5822,
    lng: -95.7607,
    heroCopy: 'cake "Honey"',
  },
  {
    weekday: "Tue",
    weekdayFull: "Tuesday",
    neighborhood: "Fulshear",
    city: "Fulshear",
    lat: 29.6919,
    lng: -95.8905,
    heroCopy: 'cake "Napoleon"',
  },
  {
    weekday: "Wed",
    weekdayFull: "Wednesday",
    neighborhood: "Katy",
    city: "Katy",
    lat: 29.7858,
    lng: -95.8244,
    heroCopy: 'cake "Red Velvet"',
  },
  {
    weekday: "Thu",
    weekdayFull: "Thursday",
    neighborhood: "Cypress",
    city: "Cypress",
    lat: 29.9691,
    lng: -95.6972,
    heroCopy: 'cake "Pistachio Roll"',
  },
  {
    weekday: "Fri",
    weekdayFull: "Friday",
    neighborhood: "The Woodlands",
    city: "The Woodlands",
    lat: 30.1658,
    lng: -95.4793,
    heroCopy: 'cake "Milk Maiden"',
  },
];

const WINDOW_LOCAL = "15:00:00-05:00";
const WINDOW_END_LOCAL = "19:00:00-05:00";

// Next-occurring date (Central Time, naive) for a given weekday, relative to today.
// Server-rendered, deterministic per-deploy day; this is a schedule hint, not
// a billing surface, so day-precision is enough.
function nextDateFor(weekday: Stop["weekday"], today: Date): string {
  const map = { Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5 } as const;
  const target = map[weekday];
  const cur = today.getUTCDay();
  const diff = (target - cur + 7) % 7 || 7;
  const d = new Date(today);
  d.setUTCDate(d.getUTCDate() + diff);
  return d.toISOString().slice(0, 10);
}

// Map projection. Source bounds derived from STOPS; the metro-wide route is
// taller than it is wide, so the viewBox is portrait with 50px padding.
const VIEW_W = 560;
const VIEW_H = 720;
const PAD = 50;
const MIN_LNG = -95.8905;
const MAX_LNG = -95.4793;
const MIN_LAT = 29.5822;
const MAX_LAT = 30.1658;

function project(lat: number, lng: number): { x: number; y: number } {
  const innerW = VIEW_W - PAD * 2;
  const innerH = VIEW_H - PAD * 2;
  const x = PAD + ((lng - MIN_LNG) / (MAX_LNG - MIN_LNG)) * innerW;
  const y = PAD + (1 - (lat - MIN_LAT) / (MAX_LAT - MIN_LAT)) * innerH;
  return { x, y };
}

// Label offsets keep text from overlapping pins on the static layout.
const LABEL_OFFSETS: Record<Stop["weekday"], { dx: number; dy: number; anchor: "start" | "end" | "middle" }> = {
  Mon: { dx: 0, dy: -18, anchor: "middle" },
  Tue: { dx: 14, dy: 5, anchor: "start" },
  Wed: { dx: 14, dy: 5, anchor: "start" },
  Thu: { dx: 14, dy: 5, anchor: "start" },
  Fri: { dx: -14, dy: 5, anchor: "end" },
};

export default function HappyPath() {
  const today = new Date();
  const stopsWithDate = STOPS.map((s) => ({ ...s, date: nextDateFor(s.weekday, today) }));

  const eventsJsonLd = {
    "@context": "https://schema.org",
    "@graph": stopsWithDate.map((s) => ({
      "@type": "Event",
      name: `HappyCake truck — ${s.neighborhood}`,
      description: `HappyCake food truck stop in ${
        s.neighborhood === s.city ? s.city : `${s.neighborhood}, ${s.city}`
      }. Hero of the day: ${s.heroCopy}, plus the ready-made line. Pickup only — no pre-order required.`,
      startDate: `${s.date}T${WINDOW_LOCAL}`,
      endDate: `${s.date}T${WINDOW_END_LOCAL}`,
      eventSchedule: {
        "@type": "Schedule",
        repeatFrequency: "P1W",
        byDay: `https://schema.org/${s.weekdayFull}`,
        startTime: "15:00:00-05:00",
        endTime: "19:00:00-05:00",
      },
      eventStatus: "https://schema.org/EventScheduled",
      eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
      location: {
        "@type": "Place",
        name: s.neighborhood === s.city ? s.city : `${s.neighborhood}, ${s.city}`,
        address: {
          "@type": "PostalAddress",
          addressLocality: s.city,
          addressRegion: "TX",
          addressCountry: "US",
        },
        geo: { "@type": "GeoCoordinates", latitude: s.lat, longitude: s.lng },
      },
      organizer: { "@id": `${SITE_URL}/#org` },
      url: PAGE_URL,
    })),
  };

  const todayWeekday = today.toLocaleDateString("en-US", { weekday: "short", timeZone: "America/Chicago" });
  const nextStop = stopsWithDate.find((s) => s.weekday === todayWeekday) ?? stopsWithDate[0];

  return (
    <div className="space-y-10">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(eventsJsonLd) }}
      />

      <header>
        <p className="uppercase tracking-widest text-xs text-happy-blue-500 font-medium">
          The Happy Path
        </p>
        <h1 className="font-display text-4xl md:text-5xl text-happy-blue-900 mt-2">
          The truck on the road, every weekday.
        </h1>
        <p className="mt-4 text-lg text-ink/80 max-w-2xl">
          We park 3:00&nbsp;PM&nbsp;–&nbsp;7:00&nbsp;PM in a different
          neighbourhood Mon–Fri. Be there at the right time and grab a cake on
          the way home — no pre-order needed, ready-made line plus the hero of
          the day.
        </p>
      </header>

      <section className="rounded-2xl border border-cream-200 bg-cream-50/60 p-4 sm:p-6">
        <div className="flex items-baseline justify-between flex-wrap gap-2 mb-4">
          <h2 className="font-display text-2xl text-happy-blue-900">This week&rsquo;s stops</h2>
          <p className="text-sm text-ink/70">
            Next: <strong className="text-happy-blue-700">{nextStop.weekdayFull}</strong> in {nextStop.neighborhood}
          </p>
        </div>

        <svg
          viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
          className="w-full h-auto mx-auto max-w-md"
          role="img"
          aria-label="Map of HappyCake truck weekly stops across Richmond, Fulshear, Katy, Cypress, and The Woodlands."
        >
          {/* Backdrop */}
          <rect x="0" y="0" width={VIEW_W} height={VIEW_H} fill="#FBF7EE" />

          {/* Compass-style grid hint */}
          <g stroke="#E8DFC8" strokeWidth="1" strokeDasharray="2 4">
            <line x1={PAD} y1={VIEW_H / 2} x2={VIEW_W - PAD} y2={VIEW_H / 2} />
            <line x1={VIEW_W / 2} y1={PAD} x2={VIEW_W / 2} y2={VIEW_H - PAD} />
          </g>

          {/* Route polyline through the week, Mon → Fri */}
          <polyline
            points={STOPS.map((s) => {
              const { x, y } = project(s.lat, s.lng);
              return `${x.toFixed(1)},${y.toFixed(1)}`;
            }).join(" ")}
            fill="none"
            stroke="#5B7FB5"
            strokeWidth="2"
            strokeDasharray="6 5"
            strokeLinejoin="round"
          />

          {/* Metro caption */}
          <text
            x={VIEW_W / 2}
            y={VIEW_H - 18}
            textAnchor="middle"
            className="fill-ink/40"
            style={{ fontSize: 12, letterSpacing: "0.15em", textTransform: "uppercase" }}
          >
            Greater Houston · west &amp; north arc
          </text>

          {/* Stop pins */}
          {STOPS.map((s) => {
            const { x, y } = project(s.lat, s.lng);
            const lbl = LABEL_OFFSETS[s.weekday];
            const isNext = s.weekday === nextStop.weekday;
            return (
              <g key={s.weekday}>
                <circle cx={x} cy={y} r={isNext ? 14 : 9} fill={isNext ? "#E8775A" : "#1F4471"} opacity={isNext ? 0.18 : 0.12} />
                <circle cx={x} cy={y} r="6" fill={isNext ? "#E8775A" : "#1F4471"} />
                <text
                  x={x + lbl.dx}
                  y={y + lbl.dy}
                  textAnchor={lbl.anchor}
                  className="fill-happy-blue-900"
                  style={{ fontSize: 13, fontWeight: 600 }}
                >
                  {s.weekday} · {s.neighborhood}
                </text>
                <text
                  x={x + lbl.dx}
                  y={y + lbl.dy + 14}
                  textAnchor={lbl.anchor}
                  className="fill-ink/60"
                  style={{ fontSize: 11 }}
                >
                  {s.heroCopy}
                </text>
              </g>
            );
          })}
        </svg>

        <p className="mt-3 text-xs text-ink/50">
          Schematic map. Exact corner is set by the truck driver the morning of
          — check WhatsApp for the day&rsquo;s pin.
        </p>
      </section>

      <section>
        <h2 className="font-display text-2xl text-happy-blue-900 mb-4">Schedule</h2>
        <div className="overflow-x-auto rounded-xl border border-cream-200">
          <table className="w-full text-sm">
            <thead className="bg-cream-50 text-happy-blue-700 text-left">
              <tr>
                <th className="px-4 py-3 font-medium">Day</th>
                <th className="px-4 py-3 font-medium">Neighbourhood</th>
                <th className="px-4 py-3 font-medium">Window</th>
                <th className="px-4 py-3 font-medium">Hero of the day</th>
              </tr>
            </thead>
            <tbody>
              {stopsWithDate.map((s) => (
                <tr key={s.weekday} className="border-t border-cream-200">
                  <td className="px-4 py-3">
                    <div className="font-medium text-happy-blue-900">{s.weekdayFull}</div>
                    <div className="text-xs text-ink/50">next: {s.date}</div>
                  </td>
                  <td className="px-4 py-3">
                    {s.neighborhood === s.city ? (
                      <div>
                        {s.city}
                        <span className="text-xs text-ink/60">, TX</span>
                      </div>
                    ) : (
                      <>
                        <div>{s.neighborhood}</div>
                        <div className="text-xs text-ink/60">{s.city}, TX</div>
                      </>
                    )}
                  </td>
                  <td className="px-4 py-3">3:00 – 7:00 PM</td>
                  <td className="px-4 py-3 italic">{s.heroCopy}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="grid sm:grid-cols-3 gap-4 text-sm">
        <div className="rounded-xl border border-cream-200 p-4">
          <p className="font-medium text-happy-blue-900">Pickup only</p>
          <p className="mt-1 text-ink/70">No pre-order needed at the truck. Cash, card, and tap-to-pay.</p>
        </div>
        <div className="rounded-xl border border-cream-200 p-4">
          <p className="font-medium text-happy-blue-900">Want a whole cake set aside?</p>
          <p className="mt-1 text-ink/70">
            Send a <a href="https://wa.me/12819798320" className="text-happy-blue-700 underline">WhatsApp</a> by 1:00 PM and we&rsquo;ll bring it on the truck.
          </p>
        </div>
        <div className="rounded-xl border border-cream-200 p-4">
          <p className="font-medium text-happy-blue-900">Don&rsquo;t see your block?</p>
          <p className="mt-1 text-ink/70">
            Order pickup at <a href="/order" className="text-happy-blue-700 underline">/order</a> from our Sugar Land kitchen.
          </p>
        </div>
      </section>
    </div>
  );
}
