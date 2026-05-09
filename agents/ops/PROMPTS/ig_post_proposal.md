# Prompt template — Instagram post proposal (canonical owner-gate)

> The orchestrator (or `scripts/smoke_ig_post.sh`) fills `{{trigger}}`,
> `{{trigger_detail}}`, `{{stage}}`, and (for stage=publish only)
> `{{scheduled_post_id}}` before piping this to `claude -p` from
> `agents/ops/`. Read `CLAUDE.md` in this folder for the role contract;
> this prompt is the per-event procedure.

---

A content trigger fired for HappyCake's Instagram. Two stages — the
orchestrator runs each in a separate `claude -p` invocation:

- **stage=propose** — kitchen / product trigger fired; you draft the
  caption, schedule via `instagram_schedule_post`, and return the
  owner-gate JSON. The orchestrator forwards it to the owner via
  Telegram.
- **stage=publish** — owner approved in Telegram; the orchestrator has
  already called `instagram_approve_post`; you call
  `instagram_publish_post` and stop.

You will be called with exactly one stage. Read the variables and act
accordingly.

Stage: {{stage}}
Trigger: {{trigger}}
Trigger detail: {{trigger_detail}}
Scheduled post id (publish stage only): {{scheduled_post_id}}

## Procedure — `stage=propose`

**Step A — Draft the caption.** Use brandbook §2 + §5:

- **Use the wordmark HappyCake** (one word, two capitals). Never
  *Happy Cake* or `"HappyCake"`.
- **Cake names in straight quotes after the word *cake***: cake
  "Honey", cake "Pistachio Roll".
- **Open with the action** (brandbook §7 soft rule 1): *Today's bake
  is out…* / *Fresh out of the oven —* / *Honey cake by the slice
  through Saturday.* Not *We are happy to announce…*.
- **Specifics over adjectives.** *1.2 kg, $42, ready by noon* over
  *generously sized*. Cite the trigger: if `{{trigger_detail}}` says
  the kitchen has whole honey cakes, name the size and the price.
- **≤4 short sentences or 4 bullets** — lists, not walls. Captions
  for IG can be a touch warmer than WhatsApp, brandbook §7 soft rule 6.
- **Three emoji maximum, often zero.** Never in price lines.
- **Close with a soft CTA** (brandbook §7 soft rule 5): *Order on the
  site at happycake.us or send a message on WhatsApp.*
- **Two epithets max** in any product description. Avoid
  *amazing / unbelievable / incredible*. Prefer *lovely / fresh /
  tender / warm / honest*.

**Step B — Schedule the post.** Call exactly once:

```
mcp__happycake__instagram_schedule_post({
  imageUrl: "<stable URL — see CLAUDE.md hard rule 4>",
  caption: "<the caption you drafted in Step A>"
})
```

Use `https://happycake.us/static/honey-cake.jpg` as the placeholder
imageUrl unless `{{trigger_detail}}` carries a more specific product
photo path. The sandbox does not validate the image — but the URL has
to be present and shaped like a real CDN path.

Capture the returned `scheduledPostId`.

**Step C — Return the owner-gate JSON.** This is the canonical owner-
gate pattern; **always** treat IG publish as needing approval, even if
the kitchen drove the trigger. Output ONLY:

```json
{
  "needs_approval": true,
  "summary": "<2-3 sentences for the owner — what triggered the post, what's in it>",
  "draft": "<the exact caption you scheduled>",
  "trigger": "ig_post_publish",
  "channel": "instagram",
  "ref_id": "<scheduledPostId from Step B>"
}
```

No prose before, no prose after, no `instagram_publish_post` call. The
orchestrator forwards this to the owner via Telegram inline keyboard;
when the owner taps Approve, the orchestrator records
`instagram_approve_post(scheduledPostId)` and re-invokes you with
`stage=publish`.

## Procedure — `stage=publish`

**Step A — Verify approval landed.** The orchestrator only sets
`stage=publish` after `instagram_approve_post` succeeded; trust that
contract. (`instagram_publish_post` would error hard if approval
hadn't landed — that's the safety net.)

**Step B — Publish.** Call exactly once:

```
mcp__happycake__instagram_publish_post({
  scheduledPostId: "{{scheduled_post_id}}"
})
```

**Step C — Final stdout.** One short paragraph (≤3 sentences) for the
team channel:

- which scheduled post was published (`scheduledPostId`),
- the caption headline (paraphrase, not verbatim),
- the trigger that originally fired the proposal.

No JSON wrapper. The orchestrator does not need to re-route an
approval — the post is live.

## Hard rules (recap, see CLAUDE.md for full list)

- **HappyCake** is one word, two capitals.
- Cake names in straight quotes after the word *cake*.
- Caption is English only.
- Never invent product specs not present in `{{trigger_detail}}`.
- Never call `instagram_publish_post` in the same turn you scheduled.
- Never echo `STEPPE_MCP_TOKEN` or any auth header.

## Pre-finish checklist

If `stage=propose`:

- [ ] My caption uses **HappyCake** and cake-name quotes correctly.
- [ ] I called `instagram_schedule_post` exactly once.
- [ ] My final stdout is ONLY the owner-gate JSON with
      `trigger="ig_post_publish"` and `ref_id` set to the
      `scheduledPostId`.
- [ ] I did not call `instagram_publish_post` (that's the next stage).

If `stage=publish`:

- [ ] I called `instagram_publish_post` exactly once with
      `scheduledPostId={{scheduled_post_id}}`.
- [ ] My final stdout is the one-paragraph completion report — no
      JSON wrapper.

If any unchecked, fix it before finishing.

Begin now.
