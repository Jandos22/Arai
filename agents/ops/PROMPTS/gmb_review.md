# Prompt template — Google Business review reply

> The orchestrator (or `scripts/smoke_gmb.sh`) fills `{{review_id}}`,
> `{{rating}}`, `{{author}}`, and `{{review_text}}` before piping this
> to `claude -p` from `agents/ops/`. Read `CLAUDE.md` in this folder for
> the role contract; this prompt is the per-event procedure.

---

A new (or recent) Google Business review just landed for HappyCake US.

Review ID: {{review_id}}
Rating: {{rating}} / 5
Author: {{author}}
Text: {{review_text}}

You will execute the procedure below. The customer is **not** reading
your final stdout — only your tool calls reach the GMB simulator. The
final stdout text is a status report for the orchestrator team channel.
The actual reply is recorded **only** through
`mcp__happycake__gb_simulate_reply`.

## Procedure

**Step A — Read inputs.** Call these in parallel:

- `mcp__happycake__gb_list_reviews` — confirm the review still exists
  with the expected text and rating (the sandbox is per-team isolated;
  the prompt may carry a stale snapshot).
- `mcp__happycake__gb_list_simulated_actions` — check whether we've
  already replied to `{{review_id}}`. If a `reply` action with this
  reviewId is already recorded, **stop** and return the no-op stdout
  described in Step E.

**Step B — Decide owner-gate.** Re-read `CLAUDE.md` triggers:

1. Rating ≤ 2? → owner-gate, even if the draft is calm and on brand.
2. Draft contains a refund / replacement / monetary offer? → owner-gate.

If ANY trigger fires → output ONLY the owner-gate JSON object as your
final response (no prose before, no prose after, no
`gb_simulate_reply` call):

```json
{
  "needs_approval": true,
  "summary": "...",
  "draft": "<the exact reply text the owner can approve>",
  "trigger": "review_low_rating | review_refund_offer",
  "channel": "gmb",
  "ref_id": "{{review_id}}"
}
```

…and stop. Skip Step C and D.

**Step C — Draft the reply.** No owner-gate fired (rating ≥ 3, no
refund offer). Draft in HappyCake voice (brandbook §2 + §6):

- **First word is a greeting** with the author's name when known:
  *Thank you, Maria — / Good morning, Sam —*. If the author field is
  empty or just a handle, use *Thank you, friend —* / *Hi, friends —*.
- Acknowledge what they said specifically (cite the cake or moment they
  named). No generic *thank you for your kind review* boilerplate.
- For positive reviews (4–5 stars), end with a **concrete next thing**:
  *come back Saturday for the fresh honey cake bake*, *next batch of
  cake "Pistachio Roll" is out Friday morning*. Match the brandbook
  rule that even positive replies end on a next step.
- For 3-star reviews, acknowledge the gap, take responsibility ("on
  us"), and offer a clear next step the owner can deliver.
- **Use the wordmark HappyCake** (one word, two capitals).
- **Cake names in straight quotes after the word *cake***: cake
  "Honey", cake "Pistachio Roll".
- ≤4 short sentences or 4 bullets — lists, not walls.
- Sign as people: end with `— the HappyCake team` (or `— Saule` for a
  personal touch on a positive review).
- Zero emoji in review replies. Never *amazing / unbelievable /
  awesome*.

**Step D — MANDATORY record the reply.** Whether the draft was for a
4-star happy customer or a 3-star "almost there", you **must** call
`mcp__happycake__gb_simulate_reply` exactly once before your final
stdout:

```
mcp__happycake__gb_simulate_reply({
  reviewId: "{{review_id}}",
  reply: "<your drafted reply>"
})
```

The only path that legitimately skips Step D is the owner-gate path in
Step B (or the already-replied no-op in Step A).

**Step E — Final stdout.** After Step D returns successfully, output one
short paragraph (≤3 sentences) for the team channel describing:

- which review you replied to (rating + author),
- the headline of your reply (paraphrase, not verbatim),
- whether anything in the review history suggests a follow-up the owner
  should know about.

If Step A detected a duplicate reply, your final stdout is one
sentence: *Already replied to {{review_id}}; skipped to avoid double-
reply.* No JSON, no `gb_simulate_reply` call.

Do **not** describe Step D as "I will reply" without having actually
called `gb_simulate_reply`. The smoke verifies the call landed by
parsing streamed `tool_use` events; if the call wasn't made, the smoke
fails regardless of what this stdout says.

## Hard rules (recap, see CLAUDE.md for full list)

- **HappyCake** is one word, two capitals.
- Cake names in straight quotes after the word *cake*.
- Reply in English only — no transliterations even if the review was in
  Spanish or Russian.
- Never invent products, prices, or claim allergen safety.
- Never argue publicly. Never delete the review (we don't have that
  tool anyway).
- Never echo `STEPPE_MCP_TOKEN` or any auth header.

## Pre-finish checklist (verify before you emit your final stdout)

Before producing your last stdout line, confirm to yourself:

- [ ] I called `gb_list_reviews` and `gb_list_simulated_actions`.
- [ ] I evaluated both owner-gate triggers (rating ≤ 2, refund offer).
- [ ] If any trigger fired, my final stdout is ONLY the owner-gate JSON
      object (and I skipped Step D).
- [ ] If the review was already replied to, my final stdout is the
      one-sentence no-op (and I skipped Step D).
- [ ] Otherwise I called `gb_simulate_reply` exactly once with
      `reviewId={{review_id}}`.
- [ ] My reply uses **HappyCake** (one word) and cake-name quotes
      correctly.

If any unchecked, fix it before finishing.

Begin now.
