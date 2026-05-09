# Owner-gate rules

> Operational checklist for the sales agent. The full rules and rationale
> live in `agents/sales/CLAUDE.md`. This file is the cheat sheet — when
> any row matches, the agent stops and returns the owner-gate JSON.

## What triggers the gate

| Trigger | What to look for | Why |
|---|---|---|
| **Custom decoration** | "with my daughter's name + cartoon", "tiered", "photo on top", "fondant", "themed" — anything beyond a piped first name on a ready-made cake | We're a ready-made bakery; custom decoration introduces variability we don't promise. |
| **Allergy promise** | Any "is this safe for nut/gluten/dairy/X?" question | This kitchen does not certify allergen-free production; only Askhat decides what we say. |
| **Order > $80** | Sum of `priceCents × quantity` from `square_list_catalog` > $80 | High-value orders deserve owner sign-off on capacity and timing. Office dessert box ($120) and custom birthday cake ($95) trip this on their own. |
| **Lead-time miss** | Customer's requested pickup is sooner than the product's `leadTimeMinutes` from `kitchen_get_menu_constraints` | We don't promise what the kitchen can't deliver. Honey cake slice 5 min · pistachio roll 20 min · whole honey cake 60 min · office dessert box 180 min · custom birthday cake 1,440 min. |
| **`requiresCustomWork: true`** | `kitchen_get_menu_constraints[].requiresCustomWork` is true on any line item | Currently flips for `custom-birthday-cake` and `office-dessert-box`. |
| **Emotional / complaint** | "Disappointed", "the last one was…", refund / replacement, anger, "we never received…" | Owner replies to complaints. Agent drafts but does not send. |

## Owner-gate response shape

```json
{
  "needs_approval": true,
  "summary": "<2-3 sentences for the owner>",
  "draft_reply": "<exact text the owner can approve>",
  "trigger": "custom_decoration | allergy | over_$80 | lead_time | emotional | requires_custom_work",
  "channel": "whatsapp" | "instagram",
  "to": "<E.164 phone | IG threadId>"
}
```

The orchestrator's `_extract_json` (in `orchestrator/handlers/whatsapp.py`)
walks the first balanced `{...}` block. So:

- The JSON must be the first `{` in the response.
- No prose before it (a single short greeting is fine, but no `{` before the gate object).
- No code fences are required; if you use them, the parser will skip past them, but it's cleaner without.

## Things that are NOT triggers

- A piped first name on a ready-made cake → fine, mention it in the order note.
- "Do you have honey cake today?" → catalog read + reply, no gate.
- Pickup time later than `leadTimeMinutes` → fine, take the order.
- Two slices and a pistachio roll = $26.50 → fine, well under $80.
- "Where are you located?" / "What time do you close?" → answer from website
  policies if you have them, escalate only if you don't.
