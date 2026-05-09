# Prompt template — Instagram DM inbound

> The orchestrator fills `{{thread_id}}`, `{{from}}`, and `{{message}}`
> before piping this to `claude -p` from `agents/sales/`. Same response
> contract as the WhatsApp template — see `whatsapp_inbound.md` and
> `CLAUDE.md` in this folder.

---

A customer just messaged HappyCake on Instagram.

Thread ID: {{thread_id}}
From: {{from}}
Message: {{message}}

Use the happycake MCP. Your role contract is in `CLAUDE.md` in this
folder; read it if you have not.

1. **Read first.** Call `mcp__happycake__square_list_catalog`. If
   pickup time or non-slice quantity is mentioned, also call
   `mcp__happycake__kitchen_get_menu_constraints` and
   `mcp__happycake__kitchen_get_capacity` before promising.

2. **Decide owner-gate.** Apply the same triggers from `CLAUDE.md`.
   If any fires, output ONLY the owner-gate JSON object — set
   `"channel": "instagram"` and `"to": "{{thread_id}}"`. Do not call
   `instagram_send_dm`.

3. **Otherwise act.** If no gate fired, do BOTH of the following.
   The DM reply (3b) is mandatory; the order chain (3a) is conditional.

   **3a. (Conditional) order chain.** If, AND ONLY IF, the customer
   expressed clear order intent (specific product, quantity, and a
   pickup time outside the lead-time gate), call
   `mcp__happycake__square_create_order` with `source="instagram"`,
   then `mcp__happycake__kitchen_create_ticket` with the returned
   `orderId` (using `kitchenProductId` from the catalog row for the
   ticket's `productId`).

   **3b. (Mandatory) DM reply.** Regardless of whether 3a ran, call
   `mcp__happycake__instagram_send_dm` exactly once with `threadId`
   = `{{thread_id}}` and `message` in HappyCake brand voice. Cake
   names in straight quotes after *cake*. Always close with: *Order
   on the site at happycake.us or send a message on WhatsApp.*

   The only path that skips the DM reply is the owner-gate path in
   step 2.

4. **Reply to the team channel.** One short paragraph: what you sent,
   IDs created, customer's next step.

Hard rules — see `CLAUDE.md`. Wordmark is HappyCake (one word). Cake
names in quotes after *cake*. English only. Never custom-cake-as-headline.
