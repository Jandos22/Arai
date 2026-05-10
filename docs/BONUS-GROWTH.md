# Growth-upside bonus map

> Hackathon brief §9 awards up to **+5 bonus points** for growth upside:
> lead scoring, local SEO, referrals, WhatsApp follow-up, upsell logic,
> marketing budget optimization. This doc points the evaluator at where
> each one lives and what evidence to look for.

## 1. Lead scoring — every WhatsApp inbound

- Code: `orchestrator/growth.py` (`score_whatsapp_lead`,
  `LeadScore`).
- Wiring: `orchestrator/handlers/whatsapp.py` writes a `lead_score`
  evidence row on every inbound and forwards the segment + reasons into
  the Telegram owner-approval card (`orchestrator/telegram_bot.py`,
  `request_approval` lead-chip block).
- Evidence event: `lead_score` (channel, score 0–100, segment
  `hot|warm|low`, route, reasons, evidenceSources).
- Test: `orchestrator/tests/test_whatsapp_growth.py`.

## 2. Local SEO — Sugar Land discoverability

- LocalBusiness/Bakery JSON-LD on every page:
  `website/app/layout.tsx` (areaServed: Sugar Land, Missouri City,
  Stafford, Richmond, Houston).
- City landing page: `website/app/sugar-land-custom-cakes/page.tsx`
  with `Service` + `FAQPage` JSON-LD targeting "sugar land custom
  cakes", "sugar land birthday cake", "sugar land medovik".
- Product pages emit `Product` schema with price + stock state:
  `website/app/products/[slug]/page.tsx`.
- Sitemap: `website/app/sitemap.ts` includes the city page at priority
  0.85.
- Robots: `website/app/robots.ts` allows all and points at the sitemap.

## 3. Referrals — issued on follow-up, redemption tracked on inbound

- Code: `orchestrator/referrals.py` (`code_for`, `detect_codes`,
  `ReferralStore`, `referral_pitch`). Codes are deterministic
  `HAPPY-XXXX` from a SHA-1 of the customer identifier — re-issue is
  idempotent.
- Issuance: `handlers/whatsapp.py::handle_follow_up_due` appends the
  referral pitch to every pickup follow-up and writes a
  `referral_issued` evidence row.
- Redemption: `handlers/whatsapp.py::handle` scans every inbound for
  `HAPPY-XXXX` codes, records the attempt in
  `evidence/referrals.json`, and writes a `referral_redeemed`
  evidence row (with `matched: true|false` and the issuer identifier
  when matched).

## 4. WhatsApp follow-up — pickup reminder + abandoned-cart loop

- Pickup follow-up: `handlers/whatsapp.py::handle_follow_up_due` →
  `growth.py::build_pickup_follow_up_message` → `whatsapp_send`. Now
  carries the referral pitch.
- Abandoned-cart scheduler: `handlers/abandoned.py`, scheduled tick
  routed in `main.py::build_routing_table` (`schedule:abandoned_tick`).
- Repeat-customer one-tap reorder: `orchestrator/customers.py`
  (`propose_reorder`), used on inbound greetings.
- Evidence events: `whatsapp_follow_up_sent`, `proposed_reorder`,
  `abandoned_cart_*`.

## 5. Upsell logic — one add-on per completed order

- Website assistant: `website/lib/upsell.ts`
  (`suggestUpsell`) — deterministic rules: celebration cake → candle
  set + piped name; signature whole cake → trial slice of another SKU;
  order ≥ $80 → local delivery quote. Wired into
  `website/app/api/assistant/route.ts` on the `order_intent` path; emits
  an `upsell_offered` evidence entry inside the JSON response.
- Sales agent: `agents/sales/CLAUDE.md` rule §3a — one-line upsell on
  Path 2 (completed) orders only, never on owner-gate / complaint /
  custom-cake paths. Brand-voice constrained.

## 6. Marketing budget optimization — $500/month, evidenced

- Plan + run logs: `docs/MARKETING.md` — single-cycle plan with
  margin, conversion, and lead-quality assumptions; multiple iteration
  run logs against `marketing_get_budget`,
  `marketing_get_sales_history`, and `marketing_get_campaign_metrics`.
- Agent: `agents/marketing/CLAUDE.md`, invoked on
  `marketing:tick` events; reads MCP, proposes reallocation, escalates
  major shifts to owner Telegram for approval.
- Evidence events: `marketing_tick`, `marketing_*` MCP calls, owner
  approval rows.

## How to verify

```bash
# orchestrator unit tests (lead scoring, growth, dispatcher, referrals helpers)
cd orchestrator && .venv/bin/python -m pytest -q

# website build (sugar-land page + sitemap)
cd website && npm run build

# live smoke (sandbox MCP token required)
source scripts/load_env.sh && arai_load_env "$PWD"
cd orchestrator && .venv/bin/python -m orchestrator.main \
  --scenario launch-day-revenue-engine --max-events 40
# then grep evidence/orchestrator-<runId>.jsonl for:
#   lead_score, upsell_offered, referral_issued, referral_redeemed,
#   whatsapp_follow_up_sent, marketing_tick
```
