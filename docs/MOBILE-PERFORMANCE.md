# Mobile performance proof

Date: 2026-05-10

Target: production Next.js build served locally at `http://localhost:3737/`.

Command:

```bash
cd website
npm run build
npm start -- -p 3737
npx --yes lighthouse@12.6.1 http://localhost:3737 \
  --form-factor=mobile \
  --screenEmulation.mobile \
  --throttling-method=simulate \
  --only-categories=performance,accessibility,best-practices,seo \
  --chrome-path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --chrome-flags="--headless=new --no-sandbox" \
  --output=json \
  --output=html \
  --output-path=../evidence/lighthouse-mobile-home \
  --quiet
```

## Result

| Category | Score |
|---|---:|
| Performance | 91 |
| Accessibility | 95 |
| Best practices | 100 |
| SEO | 92 |

Key mobile timings from the final Lighthouse run:

| Metric | Result |
|---|---:|
| First Contentful Paint | 0.8 s |
| Largest Contentful Paint | 3.5 s |
| Total Blocking Time | 0 ms |
| Cumulative Layout Shift | 0 |
| Speed Index | 0.8 s |
| Time to Interactive | 3.5 s |

Evidence artifacts:

- [`evidence/lighthouse-mobile-home.report.html`](../evidence/lighthouse-mobile-home.report.html)
- [`evidence/lighthouse-mobile-home.report.json`](../evidence/lighthouse-mobile-home.report.json)

## Fixes made

- Replaced render-blocking Google Fonts stylesheet tags with `next/font/google`
  in [`website/app/layout.tsx`](../website/app/layout.tsx).
- Added smaller home-page WebP variants under `website/public/brand/home` and
  pointed the mobile-critical home hero and featured cake cards at those files
  in [`website/app/page.tsx`](../website/app/page.tsx).
- Tightened the mobile header so the WhatsApp CTA no longer wraps and the
  header does not crowd the viewport.
