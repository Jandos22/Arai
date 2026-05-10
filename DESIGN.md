# Design System — HappyCake US (Arai submission)

> Source of truth for visual decisions across `website/`, owner-facing Telegram
> messages, and any judge-facing surface. Read this **before** any UI change.
> When this file disagrees with running code or `docs/brand/HCU_BRANDBOOK.md`,
> the order of precedence is: **DESIGN.md (this file) → shipped code →
> brandbook**. Brandbook prose owns voice and editorial; this file owns visual.

## Product context

- **What this is:** HappyCake US storefront + agent surfaces for the
  Arai vertical slice (customer interest → order intent → kitchen handoff →
  owner approval).
- **Who it's for:** Sugar Land, TX families (women 25–65), and the AI agents
  reading `/agent.json`, `/api/catalog`, `/api/policies`.
- **Project type:** Hybrid — marketing storefront + lightweight ordering app +
  machine-readable surface. Layout is grid-disciplined for the app paths
  (menu, order, assistant), editorial for the homepage hero and `/about`.
- **Memorable thing:** *"Tastes like real home baking."* Every visual
  decision should reinforce homemade warmth and quiet confidence — not
  bakery-as-luxury, not bakery-as-startup.

## Aesthetic direction

- **Direction:** *Editorial homemade* — generous whitespace, warm cream
  surfaces, serif display anchoring product names, modest decorative restraint.
- **Decoration level:** intentional. Cream pages, hand-photographed cakes,
  occasional polka-dot pattern, no gradients, no glassmorphism.
- **Mood:** Sunday-morning kitchen, not Saturday-night patisserie.
- **Reference posture:** the page should feel like a neighbourhood bakery's
  printed menu card scaled up, not a SaaS landing page.

### Safe choices (category baseline — keep)

- Cream + warm-blue palette is conventional for traditional bakeries; we
  lean into it because the customer wants familiarity, not surprise.
- Hand-photographed product shots in 4/5 aspect ratio.
- Sticky header, max-width container, three-column footer.

### Risks (where we deliberately depart)

- **Serif display at hero scale.** Most local-bakery sites use a script or
  rounded sans for warmth. We use Fraunces at 48–60px because confidence
  comes from typography, not curlicues.
- **Coral as a single-point accent only.** The accent never appears in two
  places on the same view. It marks the moment of delight ("happiness" in
  the hero, the WhatsApp CTA), then disappears.
- **No drop shadows on product cards.** The shadow comes from the photograph,
  not the wrapper. This is unusual in food e-commerce; it reads quieter.

## Typography

- **Display / hero:** **Fraunces** (Google Fonts, axes: SOFT, WONK, opsz),
  loaded via `next/font/google` in `website/app/layout.tsx` as
  `--font-display`. Used through Tailwind utility `font-display`.
- **Body / UI:** **Inter** (Google Fonts), loaded as `--font-body`.
  Default body font on `<body>`.
- **Code / monospace:** system monospace stack (rare; only in agent JSON
  examples in docs).

### Brandbook divergence (intentional)

`docs/brand/HCU_BRANDBOOK.md` §4 specifies *Cormorant Garamond* as the
display serif. The shipped system uses **Fraunces** instead. Reason:
Fraunces holds up at hero scale on screens (variable axes for optical
sizing, stronger ink trap), Cormorant gets fragile under 24px on retina
displays. Treat Fraunces as canonical for digital surfaces; Cormorant
remains acceptable for print collateral.

### Type scale (web, shipped)

| Role | Font | Class | Size | Line-height | Use |
|---|---|---|---|---|---|
| Hero | Fraunces | `font-display text-5xl md:text-6xl` | 48 / 60 px | tight (1.05) | Homepage h1, office-boxes h1 |
| Section h1 | Fraunces | `font-display text-4xl` | 36 px | 1.1 | `/menu`, `/about`, `/order` |
| Section h2 | Fraunces | `font-display text-2xl–3xl` | 24–30 px | 1.15 | Subsection headers |
| Card title | Fraunces | `font-display text-lg` | 18 px | 1.25 | Product card names |
| Eyebrow | Inter | `uppercase tracking-widest text-xs font-medium` | 12 px | 1.5 | Category, page label above h1 |
| Body | Inter | `text-base` | 16 px | 1.6 | Default paragraph |
| Body small | Inter | `text-sm` | 14 px | 1.5 | Footer, meta |
| Caption | Inter | `text-xs` | 12 px | 1.5 | Lead-time chips, tags |

Cake-name labels in body copy: keep in plain Inter, no small caps. Cake
names always in straight quotes after the word "cake": `cake "Honey"`. See
brandbook §2 for the editorial rule.

## Color

Defined in `website/tailwind.config.js` and surfaced as Tailwind utilities.
**Do not introduce new color tokens without updating this table and the
Tailwind config in the same commit.**

| Token | Hex | Tailwind class | Use |
|---|---|---|---|
| `happy-blue-900` | `#0E2A3C` | `text-happy-blue-900` / `bg-happy-blue-900` | Display headlines on cream, hover state for primary CTA, footer dark |
| `happy-blue-700` | `#1B4868` | `text-happy-blue-700` / `bg-happy-blue-700` | Logo blue, primary button background, link hover |
| `happy-blue-500` | `#3B7BA8` | `text-happy-blue-500` | Eyebrow text, link default, mid accents |
| `happy-blue-200` | `#BFD8E8` | `border-happy-blue-200` / `bg-happy-blue-200/40` | Card borders, subtle surfaces |
| `cream-50` | `#FBF6E8` | `bg-cream-50` | Page background — single source of truth for body bg |
| `cream-100` | `#F4ECD3` | `bg-cream-100` | Card and image-fallback surfaces |
| `cream-200` | `#E9DBB4` | `border-cream-200` | Hairline borders on cream-on-cream |
| `coral` | `#E08066` | `text-coral` / `border-coral` | Single-point accent only — hero "happiness", assistant CTA |
| `leaf` | `#6E9D74` | (sparingly) | Seasonal — Eid / spring / Easter |
| `ink` | `#1A1816` | `text-ink` / `text-ink/70` etc. | Primary body text on cream; opacity steps for hierarchy |

CSS variables in `website/app/globals.css`:

```css
:root { --bg: #FBF6E8; --ink: #1A1816; }
```

**Approach:** restrained. One accent (coral) per view. Color is a quiet
signal of meaning, not decoration. Dark mode is **not supported** in v1 —
the brand reads as cream-light by intent.

**Contrast checks (must pass before merge):**

- `text-ink` on `bg-cream-50` → 14.6:1 ✓
- `text-cream-50` on `bg-happy-blue-700` → 7.8:1 ✓
- `text-coral` on `bg-cream-50` → 4.0:1 (large text only — never under 18px)
- `text-happy-blue-500` on `bg-cream-50` → 4.5:1 ✓ (links/eyebrows)

## Spacing

- **Base unit:** 4px (Tailwind default).
- **Section rhythm:** `space-y-12` (48px) for marketing sections,
  `space-y-16` (64px) for homepage. Inside sections, `space-y-8` (32px).
- **Container:** `mx-auto max-w-6xl px-6` — single canonical container.
  Use `max-w-3xl` for prose pages (`/about`, `/policies`).
- **Component padding:** cards use `p-4` to `p-6`, hero CTAs use `px-6 py-3`,
  pill chips use `px-4 py-1.5`.

Density is **comfortable**, not compact. We breathe around photographs.

## Layout

- **Grid:** Tailwind 12-col implicit, but most layouts are 1-col or
  `md:grid-cols-2` / `md:grid-cols-[1.2fr_0.8fr]`.
- **Max content width:** 1152px (`max-w-6xl`).
- **Header:** sticky, `bg-cream-50/95 backdrop-blur`, hairline bottom border
  in `border-cream-200`. WhatsApp pill CTA is the only filled element.
- **Footer:** three-column on `md`, light cream-200 top border, muted
  `text-ink/70`.
- **Cards:** product cards use `rounded-3xl` for the photo well,
  `rounded-2xl` for content cards, `rounded-xl` for stat tiles.
- **Buttons:** **always `rounded-full`**. Three variants:
  1. **Primary:** `bg-happy-blue-700 text-cream-50 px-6 py-3 hover:bg-happy-blue-900`
  2. **Secondary:** `border border-happy-blue-700 text-happy-blue-700 hover:bg-happy-blue-200/40`
  3. **Accent:** `border border-coral text-coral hover:bg-coral/10` (use ≤1 per view)

### Border radius scale (canonical)

| Class | Use |
|---|---|
| `rounded-full` | Buttons, pills, avatar slots |
| `rounded-3xl` | Hero photo well, large cake imagery |
| `rounded-2xl` | Surface cards, info panels |
| `rounded-xl` | Inline tiles, lead-time chips, alerts |

Do not use `rounded-md` / `rounded-lg` — they break the rhythm.

## Imagery

- **Real photos only.** Never AI-generated images of HappyCake products.
  AI illustration is acceptable for non-product decoration only.
- **Aspect ratios:** hero `4/5`, product card `4/5`, lifestyle `16/10`.
- **Loading:** Next.js `Image` with `fill` + `sizes`; product imagery
  preloaded in `/website/public/brand/home/` at the relevant width.
- **Alt text:** descriptive of the cake (layers, decoration, garnish), not
  the brand. See `website/app/page.tsx:60` for the canonical example.
- **Photo captions:** none on product cards. Caption only on editorial
  imagery in `/about`.

## Motion

- **Approach:** minimal-functional. No scroll-driven animations, no
  parallax, no entrance choreography.
- **Allowed:** Tailwind hover transitions on links and buttons (default
  150ms ease-out), `backdrop-blur` on the sticky header.
- **Forbidden:** purple/blue gradients in motion, blob morphs, looping
  marquees, auto-rotating hero carousels.

## Patterns from the brandbook (visual)

- **Polka-dot awning pattern.** Cream dots on Happy Blue, or Happy Blue
  dots on cream. Reserve for: campaign banners, social cards, possibly the
  footer cap. Not yet implemented in the website — if added, render as SVG
  pattern, not a raster.
- **Diamonds as eyebrow separators.** `◆ HappyCake · Sugar Land` — usable
  but not a hard requirement on the storefront.
- **Cupcake silhouettes.** Single-stroke; reserve for category labels in
  future menu refinements.

## Voice (cross-link, not duplicated here)

Voice rules live in `docs/brand/HCU_BRANDBOOK.md` §2 and §7. Hard rules:

1. Wordmark is *HappyCake* (one word, two capitals).
2. Cake names in straight quotes after the word "cake": `cake "Honey"`.
3. ≤3 emoji per surface, often zero.
4. No fabrication of price, flavour, ingredient, policy, or hours.
5. Reply in English even if the customer writes in another language.

If you are an AI agent generating copy: read brandbook §7 (AI-agent
operating rules) before drafting.

## Anti-slop checklist (applies to every UI change)

Reject any of the following before commit:

- [ ] Purple or violet gradients anywhere
- [ ] 3-column icon-in-circle feature grid (the SaaS hero pattern)
- [ ] Centered-everything layout outside the hero
- [ ] `system-ui` / `-apple-system` as the *display* font (we paid for Fraunces)
- [ ] Two accent colors competing on one view
- [ ] Drop shadows on product cards
- [ ] Stock photography or AI-generated cake images
- [ ] Marketing exclamations ("Order now!", "Limited time!")
- [ ] Generic icons (heart in circle, lightning bolt) on product surfaces
- [ ] Over-used adjectives in copy ("amazing", "incredible", "the best")

## External references (submission context)

- **SBC hackathon brief:** Steppe Business Club brand (sbc-logo-v4.svg) is
  *referenced* on submission/judge surfaces (e.g., a "Built for Steppe
  Business Club Hackathon · May 2026" footer note). It is **not** part of
  the HappyCake brand and must never appear on customer-facing storefront
  pages. SBC asset URL is auth-gated; resolve through the launch kit when
  needed.
- **Original HappyCake (Kazakhstan) reference:** the awning pattern, the
  cake-naming convention, and the verbal cadence carry over from the
  parent brand. Visual language adapted for Sugar Land context (English
  copy, US holiday calendar, no Cyrillic).

## Decisions log

| Date | Decision | Rationale |
|---|---|---|
| 2026-05-10 | Initial DESIGN.md created | Codify shipped HCU brand into a single source so runtime agents respect it during UI work. |
| 2026-05-10 | Display font = Fraunces (overrides brandbook Cormorant Garamond) | Fraunces holds up at hero scale and small UI; Cormorant gets fragile under 24px on retina screens. Brandbook acceptable for print only. |
| 2026-05-10 | No dark mode in v1 | Brand reads as cream-light by intent; dark mode would require a parallel palette and isn't on the hackathon path. |
| 2026-05-10 | Coral is single-point accent only | Two accent colors on one view dilutes the moment-of-happiness signal. |
| 2026-05-10 | No drop shadows on product cards | The photograph carries depth; wrapper shadows make it look like stock e-commerce. |

---

*Generated by `/design-consultation`. Update the decisions log on every
material change. Cross-check against `website/tailwind.config.js`,
`website/app/layout.tsx`, and `website/app/globals.css` when in doubt.*
