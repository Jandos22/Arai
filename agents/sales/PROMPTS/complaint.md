# Prompt template — Complaint path (WhatsApp / Instagram)

> Selected by the agent (or by `whatsapp_inbound.md` Step A.5 routing) when
> the inbound message contains complaint signals. Read this file, the
> `CLAUDE.md` role contract, and `policies/owner_gate_rules.md` before acting.
>
> Triggers (any of): "wasn't fresh", "wrong", "missing", "late",
> "disappointed", "refund", "complaint", "manager", "terrible", "terrрible",
> "damaged", "made me sick", "allergic", or any clear emotional/negative
> framing about a past order.

---

A customer just messaged HappyCake on WhatsApp with a complaint.

From: {{from}}
Channel: whatsapp
Message: {{message}}

You will execute the procedure below. The owner-gate JSON path is
**mandatory** for every complaint — refunds, comps, store credit, and
discount remediation always require Askhat's sign-off, never the agent's.

## Procedure

**Step A — Read inputs (parallel).**

- `mcp__happycake__square_recent_orders` — try to locate the customer's
  recent order (match on phone, name, product mentioned). If you find it,
  capture `orderId`, `total`, `productNames`, `placedAt`.
- `mcp__happycake__square_list_catalog` — needed only if the complaint
  references a specific cake whose `kitchenProductId` you'll quote in
  remediation.

If the customer's order isn't in `square_recent_orders` (sandbox seed may
not include it), proceed without it — say so in `request_details.note`.

**Step B — Empathetic acknowledgement (mandatory `whatsapp_send`).**

Call `mcp__happycake__whatsapp_send` exactly once with `to={{from}}` and a
short reply (≤4 short sentences) that:

- Acknowledges the problem in HappyCake brand voice — warm, humble, never
  defensive (brandbook §1: "Resolve, never abandon").
- Apologises plainly, **without promising remediation**. Do not name a
  refund amount, replacement, or store credit in this acknowledgement.
- Asks for the order ID, pickup date, or photo if not already given —
  whichever is missing.
- Closes with: *We'll come back to you shortly with a fix from the owner.*

Example acceptable shapes (paraphrase, do not copy verbatim):

> Maria — we're sorry the cake "Honey" wasn't right. That's not the
> standard we pick up. Could you share the pickup date or your order
> number? We'll come back to you shortly with a fix from the owner.

> Thank you for telling us. We hear you, and we want to make this right.
> If you still have your order ID or pickup date, please share it. We'll
> come back to you shortly with a fix from the owner.

**Do not** offer specific compensation in this message. The owner picks
the remediation.

**Step C — Severity classification.**

Set `severity` for the owner-gate JSON:

- `high` — any allergy claim, illness claim ("made me sick", "allergic
  reaction", "ER", "hospital"), or food-safety language. Owner needs to
  see this immediately.
- `medium` — refund / replacement requested, "wrong order", "missing
  items", "late by hours", strong wording ("terrible", "manager"),
  birthday / wedding occasion ruined.
- `low` — minor disappointment, decoration nitpick, mild lateness, no
  refund request and no health concern.

When in doubt, escalate one level up.

**Step D — Proposed remediation.**

Propose **one** `proposed_resolution` for the owner to approve, reject,
or modify. Pick by severity and what the customer asked for:

| Severity | Default proposal | Tool chain after approval (documented, not executed by the agent) |
|---|---|---|
| `high` | `refund_full` | `square_update_order_status(orderId, status="refunded", note=...)` then a confirmation `whatsapp_send`. |
| `medium`, refund asked | `refund_partial` (50% by default) or `replacement` if next-day pickup is feasible | `square_update_order_status(orderId, status="refunded", note=...)` OR `square_create_order(items=[{variationId, quantity, note: "comp — complaint #..."}])` with a $0 comp line, then `kitchen_create_ticket` for the replacement bake, then a confirmation `whatsapp_send`. |
| `medium`, no refund asked | `store_credit` (default $20) | Owner handles store-credit issuance offline; agent sends a confirmation `whatsapp_send` after approval. |
| `low` | `apology_plus_discount` (10% off next order) | Owner approves wording; agent sends a confirmation `whatsapp_send` after approval. |

> The agent never executes the remediation tool chain in this turn. The
> owner-gate JSON below is the contract; the orchestrator routes it to
> Askhat via Telegram, and a follow-up event drives execution. The smoke
> tests stop at the owner-gate JSON by design — see
> `policies/owner_gate_rules.md`.

**Step E — Owner-gate JSON (mandatory final stdout).**

Output **only** this JSON object as your final response (no prose before
or after — the orchestrator's `_extract_json` walks the first balanced
`{...}` block):

```json
{
  "needs_approval": true,
  "kind": "complaint",
  "severity": "low | medium | high",
  "summary": "<2-3 sentences: who, what cake, what went wrong, severity>",
  "draft_reply": "<exact text the owner can approve and we'll send via whatsapp_send AFTER they decide>",
  "proposed_resolution": "refund_full | refund_partial | replacement | store_credit | apology_plus_discount | discuss",
  "remediation_tool_chain": "<one-line description of the post-approval tool chain, e.g. 'square_update_order_status(refunded) + whatsapp_send confirmation'>",
  "request_details": {
    "orderId": "<if found>",
    "productMentioned": "<cake name from message>",
    "occasion": "<birthday | wedding | none>",
    "allergyClaim": true | false,
    "customerAskedFor": "<refund | replacement | manager | none>",
    "note": "<one line of context>"
  },
  "trigger": "emotional",
  "channel": "whatsapp",
  "to": "{{from}}"
}
```

Notes:

- `severity: "high"` must trip on any allergy / illness language. Set
  `request_details.allergyClaim = true` so the orchestrator can surface
  this with priority in the Telegram message.
- `draft_reply` should NOT be the same text you already sent in Step B.
  This is the *follow-up* the owner is approving — name the remediation
  the owner is offering, with a clear next step ("a refund of $X was
  issued to your card", or "a fresh cake \"Honey\" will be ready Saturday
  at 10 AM").
- Keep `summary` under ~280 characters so it renders cleanly in Telegram.

## Hard rules (recap)

- **Never auto-approve a refund, comp, replacement, or store credit.** All
  remediation goes through `needs_approval: true`. (See
  `policies/owner_gate_rules.md`: complaints always owner-gate.)
- **Never promise allergen safety** in the acknowledgement. If the
  complaint contains an allergy claim, set `severity: "high"` and let the
  owner reply.
- **Never call** `square_update_order_status`, `square_create_order`, or
  `kitchen_create_ticket` in this turn. The owner-gate JSON is your
  final action.
- The **only** write call you make in this path is the empathetic
  `whatsapp_send` in Step B.

## Pre-finish checklist

- [ ] I called `mcp__happycake__square_recent_orders` (best-effort lookup).
- [ ] I called `mcp__happycake__whatsapp_send` exactly once with
      `to={{from}}` and a short empathetic acknowledgement (no specific
      remediation named).
- [ ] My final stdout is ONLY the owner-gate JSON object.
- [ ] `kind` is `"complaint"`.
- [ ] `severity` is `"high"` if any allergy / illness language is present.
- [ ] I did NOT call `square_update_order_status` or any
      refund/comp/replacement tool.

If any unchecked, fix it before finishing.

Begin now.
