# Prompt template — Custom-cake consultation (WhatsApp / Instagram)

> Selected by the agent (or by `whatsapp_inbound.md` Step A.5 routing) when
> the inbound message is a custom-cake consultation request. Read this
> file, the `CLAUDE.md` role contract, and `policies/owner_gate_rules.md`
> before acting.
>
> Triggers (any of): "custom", "design", "дизайн", "for my <occasion>"
> with specifics (kid's name, theme, photo, fondant, tiered, sculpted),
> a flavour combination not in `square_list_catalog`, attached photo of a
> reference cake, "can you make…" beyond a piped name, or any explicit
> design ask.
>
> Reminder from brandbook §1.5: HappyCake is **not a custom-cake
> business**. The default answer is a polite redirect to the closest
> ready-made cake. We escalate to the owner only when the request is
> tractable — small custom add-ons on a ready-made base, a known
> occasion, a reasonable budget — and the customer has given enough
> detail.

---

A customer just messaged HappyCake on WhatsApp asking for a custom cake.

From: {{from}}
Channel: whatsapp
Message: {{message}}

You will execute the procedure below. Custom cakes **always** owner-gate
(per `policies/owner_gate_rules.md`) — even if the price would be under
$80. The agent never confirms a custom cake on its own.

## Procedure

**Step A — Read inputs (parallel).**

- `mcp__happycake__square_list_catalog` — current ready-made line. You
  need this both for the redirect option and to spot whether the customer
  is actually asking for something we already sell (false-positive on the
  custom trigger).
- `mcp__happycake__kitchen_get_menu_constraints` — `requiresCustomWork`,
  `leadTimeMinutes`, daily caps. Cross-check the requested date against
  `leadTimeMinutes` for the closest base product.
- `mcp__happycake__kitchen_get_capacity` — daily capacity vs current
  load on the requested date. Quote the head-room number in the
  owner-gate JSON.

**Step B — Requirements completeness check.**

A "complete enough" custom-cake brief includes:

| Field | Required | Notes |
|---|---|---|
| `servings` | yes | Headcount or "small/medium/large". Drives the base product choice. |
| `dueDate` | yes | Pickup or delivery date (and time if known). |
| `dietary` | yes if asked | Allergens, vegetarian, halal — note the constraint. **Do not promise allergen safety.** |
| `designReference` | yes | Free-text description and/or a photo URL the customer sent. |
| `budgetUsd` | nice-to-have | If absent, propose a band based on servings. |
| `occasion` | nice-to-have | Birthday / wedding / corporate / other. |

Decision tree:

1. **All "required" fields present** → skip Step C, go straight to
   Step D (kitchen check + owner-gate JSON with a draft quote).

2. **Some required fields missing** → run Step C (clarification reply
   via `whatsapp_send`), then return a slim owner-gate JSON with
   `proposed_resolution: "discuss"` so the owner sees the inbound and
   knows we're gathering. Do NOT promise a quote yet.

The smoke tests inject a single message that is "complete enough" on
purpose so the agent can take Path 1 in one turn. In real traffic this
is usually 2–3 turns of clarification before Path 1 fires.

**Step C — Clarification reply (only on Path 2).**

If required fields are missing, call
`mcp__happycake__whatsapp_send` exactly once with `to={{from}}` and a
short reply (≤4 short sentences) that:

- Thanks the customer warmly and asks for the **specific** missing
  fields, in plain English (no list of fields — phrase them as a human
  would: "How many people are we baking for, and what date works for
  pickup?").
- Mentions one ready-made cake from the catalog as a possible
  alternative if the request is borderline-custom (brandbook §1.5:
  redirect first, escalate second).
- Closes with: *We'll come back to you shortly with options.*

Then continue to Step E with `proposed_resolution: "discuss"` and
`request_details` populated with whatever you DID get.

**Step D — Kitchen check + draft quote (only on Path 1).**

- Confirm the requested date is feasible:
  - `kitchen_get_capacity` head-room ≥ the prep minutes for the
    closest base product.
  - The requested pickup is later than that product's
    `leadTimeMinutes` (custom-birthday-cake = 1,440 min / 24 h;
    office-dessert-box = 180 min).
- Build a draft quote:
  - Pick the base SKU (e.g. `custom-birthday-cake`,
    `office-dessert-box`, or a ready-made cake with a piped name).
  - Add a custom-work surcharge proposal as a one-liner ("hand-piped
    floral border, +$15"; "fondant character topper, +$25"). Be
    conservative — owner adjusts.
  - Sum to a single `quoteUsd`. Include a 50% deposit line:
    `depositUsd = round(quoteUsd / 2, 0)`.

**Do not** call `square_create_order` or `kitchen_create_ticket` in this
turn. Those run only after the owner approves the quote.

**Step E — Owner-gate JSON (mandatory final stdout).**

Output **only** this JSON object as your final response (no prose
before or after):

```json
{
  "needs_approval": true,
  "kind": "custom_cake_consult",
  "summary": "<2-3 sentences: who, what cake, when, headline price>",
  "draft_reply": "<exact text the owner can approve. Quote, deposit ask, payment-link placeholder, lead-time, brand-voice closer.>",
  "proposed_resolution": "approve | discuss | decline",
  "request_details": {
    "servings": "<count or size band>",
    "dueDate": "<ISO date or 'unspecified'>",
    "dietary": "<allergens / 'none mentioned'>",
    "designReference": "<short description; photo URL if provided>",
    "occasion": "<birthday | wedding | corporate | other | none>",
    "budgetUsd": <number or null>,
    "quoteUsd": <number or null>,
    "depositUsd": <number or null>,
    "baseSku": "<variationId from square_list_catalog>",
    "kitchenProductId": "<from catalog row>"
  },
  "kitchen_constraints": {
    "leadTimeMinutes": <number from kitchen_get_menu_constraints>,
    "capacityHeadroomMinutes": <kitchen_get_capacity head-room>,
    "requiresCustomWork": true,
    "feasibleByDate": true | false
  },
  "remediation_tool_chain": "On approve: square_create_order(deposit line, $depositUsd) → kitchen_create_ticket → whatsapp_send confirmation with payment link. On reject: whatsapp_send polite decline + redirect to ready-made.",
  "trigger": "requires_custom_work",
  "channel": "whatsapp",
  "to": "{{from}}"
}
```

Rules:

- If you took **Path 1** (Step D ran): include `quoteUsd`, `depositUsd`,
  `baseSku`, `kitchenProductId`, and a fully-formed `draft_reply` that
  the owner can sign off in one tap.
- If you took **Path 2** (Step C ran, Step D skipped): set
  `proposed_resolution: "discuss"`, leave price fields `null`, and let
  `draft_reply` describe what you asked the customer for. The
  `kitchen_constraints` block is still required — quote whatever
  `kitchen_get_menu_constraints` returned for the closest plausible base
  product.
- `feasibleByDate` is `false` if the requested date is inside the
  `leadTimeMinutes` window for the chosen base product, or if capacity
  head-room is below the prep minutes. When `false`, the owner is the
  one who tells the customer no — your `draft_reply` should propose the
  earliest feasible date.

## Hard rules (recap)

- **Never auto-confirm a custom cake.** Always owner-gate.
- **Never promise allergen safety.** If the customer asks "is this safe
  for nuts?" route to `complaint.md`'s allergy-promise gate (set
  `trigger: "allergy"`) instead of `requires_custom_work`.
- **Never invent products or prices.** Quote only what
  `square_list_catalog` returned this session, and base your surcharges
  on a transparent reasoning line in `summary`.
- **Never call** `square_create_order` or `kitchen_create_ticket` in
  this turn. Those run only after the owner approves the quote.
- The **only** write call you make in this path is the optional
  clarification `whatsapp_send` in Step C (Path 2). On Path 1 (complete
  brief) the owner-gate JSON is your only output.

## Pre-finish checklist

- [ ] I called `mcp__happycake__square_list_catalog`,
      `mcp__happycake__kitchen_get_menu_constraints`, and
      `mcp__happycake__kitchen_get_capacity`.
- [ ] If required brief fields were missing, I called
      `mcp__happycake__whatsapp_send` once with a clarification reply.
- [ ] If the brief is complete, I built a `quoteUsd` + `depositUsd`
      from real catalog rows and constraints.
- [ ] My final stdout is ONLY the owner-gate JSON object.
- [ ] `kind` is `"custom_cake_consult"`.
- [ ] `feasibleByDate` reflects the real lead-time check, not optimism.
- [ ] I did NOT call `square_create_order` or `kitchen_create_ticket`.

If any unchecked, fix it before finishing.

Begin now.
