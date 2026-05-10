# T-013 — Sales agent: complaint + custom-cake consultation flows

> Status: completed. This card was moved from `tasks/INBOX/` to
> `tasks/DONE/` during stale-doc cleanup; the original task brief and
> acceptance checklist are preserved below.

**Owner:** Claude Code
**Dependencies:** T-005 done, ideally T-007 done first (so ops bot can also receive complaint escalations)
**Estimated:** 60–90 min
**Bonus bucket:** Real business pain (+5 — custom cake intake + complaints/refunds)

## Why

The team kit submission checklist explicitly requires:

> "On-site assistant test script: consultation, custom order, complaint, status, escalation."

T-005 covers a generic WA inquiry → reply path and an owner-gate path for high-$ orders. **It does not cover:**

1. **Custom-cake consultation** — customer wants a cake we don't have on the menu (e.g. "tres leches with mango"). Agent should: clarify (size, date, allergies, budget), check `kitchen_get_menu_constraints` + `kitchen_get_capacity`, return owner-gate JSON with full structured request. Owner reviews in Telegram, accepts/rejects with optional note.
2. **Complaint handling** — customer DMs / WAs with a problem (cake was dry, pickup was late, missing decoration). Agent should: acknowledge in brand voice, log to evidence, offer specific resolution paths (refund / replacement / store credit), AND owner-gate ALWAYS (never auto-approve a refund). If complaint contains an allergy claim → also flag with `severity: high` for immediate Telegram alert.

Both flows are big bonus-points unlocks AND hit "Depth" + "Impact" scoring dimensions hard.

## Tasks

### 1. Update `agents/sales/PROMPTS/whatsapp_inbound.md` (and `instagram_dm.md`)

Add two new step sections after the existing inquiry/order paths:

**Path D — Custom cake consultation**
- Triggers: customer mentions a cake / flavor / shape NOT in `square_list_catalog`
- Steps:
  1. Reply with a clarifying question (size, when, allergies, anything-special)
  2. After customer answers, call `kitchen_get_menu_constraints` and `kitchen_get_capacity` to check what's possible
  3. **DO NOT** auto-confirm. Return owner-gate JSON with `kind: "custom_cake_consult"`, `summary`, `request_details` (size, date, ingredients, budget hint), `kitchen_constraints` echo, `recommended_action: "discuss-with-customer" | "decline" | "approve"`
  4. NO `whatsapp_send` until owner approves

**Path E — Complaint**
- Triggers: words like "wasn't fresh", "missing", "wrong", "late", "refund", "complaint", "disappointed", "allergic", "made me sick"
- Steps:
  1. Reply with empathetic acknowledgment + ask for order ID/date if not given
  2. Look up order if possible via `square_get_order_by_id` (if available) or describe what's needed
  3. **Always** owner-gate. Return JSON with `kind: "complaint"`, `severity: "low" | "medium" | "high"` (high = allergy/health claim), `proposed_resolution: "refund" | "replacement" | "store-credit" | "discuss"`, full conversation context
  4. NO `whatsapp_send` past acknowledgment until owner approves

### 2. Add to `agents/sales/policies/owner_gate_rules.md`

New rules:
- Custom cake → ALWAYS owner-gate (regardless of price)
- Complaint → ALWAYS owner-gate
- Allergy claim in complaint → `severity: high`, also fire `marketing_report_to_owner` with urgent flag

### 3. Extend `agents/sales/scripts/smoke.sh`

Add 4 new test cases:
- D1: "Hi, can you make a tres leches cake with mango for next Saturday?" → expect Path D, owner-gate `kind: custom_cake_consult`, no auto-send beyond clarification
- D2 (followup): supply size + allergies → expect kitchen check + structured owner-gate JSON
- E1: "The Medovik I picked up yesterday wasn't fresh, can I get a refund?" → expect Path E, owner-gate `kind: complaint`, severity=medium
- E2: "My daughter had an allergic reaction to your chocolate cake" → expect Path E, owner-gate severity=HIGH

### 4. Update `evidence/sales-sample.jsonl`

Append 4 new PASS rows demonstrating each new path.

## Acceptance

- All 4 new smoke tests PASS (existing 2 still PASS)
- `evidence/sales-sample.jsonl` has 6+ entries with 4 distinct `test` values: `whatsapp_smoke`, `custom_consult_smoke`, `complaint_smoke`, `complaint_allergy_smoke`
- `agents/sales/CLAUDE.md` updated to mention 5 paths (was 3)
- Owner-gate JSON shape documented (consistent across all paths)

## Out of scope

- Actual refund execution (sandbox doesn't support it; owner approves and presumably handles offline)
- Multi-turn conversation memory (each smoke test is a single turn — fine)
- IG-specific handling beyond the existing handler

## Notes

- Brand voice from `docs/brand/HCU_BRANDBOOK.md` — empathetic, direct, never defensive on complaints
- Allergy claims get extra care — kit submission checklist mentions "allergy-safe communication" as a bonus item
- Use `evidence/EVIDENCE-SCHEMA.md` for the right `kind` values
