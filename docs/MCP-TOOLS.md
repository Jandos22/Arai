# MCP Tools — Happy Cake Sandbox

> Source: team launch kit, captured 2026-05-09 (T-001).
> Endpoint: `https://www.steppebusinessclub.com/api/mcp`
> Auth: `X-Team-Token` header. Token value lives in `.env.local` only (`STEPPE_MCP_TOKEN`). Never commit.

## Overview

The Steppe Business Club hackathon ships a **simulator-first MCP server** that stands in for Square POS, WhatsApp, Instagram, Google Business, kitchen production, marketing, a deterministic world simulator, and an evaluator. Every tool is per-team-isolated by the `X-Team-Token` header — no real third-party credentials are required, and nothing the agent does leaves the sandbox.

The launch-kit prose names the slice the evaluator scores:

> Start your demand engine with `marketing_create_campaign`, then launch, generate leads, route them, adjust, and report back to the owner. Validate production promises with `kitchen_create_ticket`, capacity checks, accept/reject decisions, and ready-for-pickup status. Use `square_create_order` and `square_get_pos_summary` to prove your website and agents can drive POS-style orders. Run `world_start_scenario` and `world_next_event` to test against the same time-compressed business day as the evaluator. Use `evaluator_get_evidence_summary` and `evaluator_generate_team_report` to preview the evidence judges will inspect.

Active token: stored only in `.env.local` (`STEPPE_MCP_TOKEN`) on the captain's MacBook. Never appears in repo history, evidence files, screenshots, or commit messages. If you suspect a leak, message the SBC organizers immediately for rotation.

## Claude Code MCP config (placeholder — replace with your real token at runtime)

```json
{
  "mcpServers": {
    "happycake": {
      "url": "https://www.steppebusinessclub.com/api/mcp",
      "headers": {
        "X-Team-Token": "sbc_team_REPLACE_WITH_YOURS"
      }
    }
  }
}
```

## Live tool catalog

55 tools across 8 namespaces. Generated from `tools/list` against the live endpoint on 2026-05-09. Required arguments in **bold**; optional in plain text.

### `square_*` — POS / orders / inventory (7)

| Tool | Required | Optional | Purpose |
|---|---|---|---|
| `square_list_catalog` | — | `limit` | List the simulator-first Happy Cake POS catalog. |
| `square_get_inventory` | **`variationIds[]`** | — | Get simulator inventory for catalog variation IDs. |
| `square_recent_orders` | — | `sinceISO`, `limit` | Fetch recent simulator POS orders for this team. |
| `square_create_order` | **`items[{variationId, quantity, note?}]`** | `source` (website\|whatsapp\|instagram\|walk-in\|agent), `customerName`, `customerNote` | Create a simulator POS order. Use `kitchen_create_ticket` after this for production handoff. |
| `square_update_order_status` | **`orderId`**, **`status`** | `note` | Update simulated POS order status (approval, handoff, ready, completion, cancellation). |
| `square_get_pos_summary` | — | — | Per-team POS summary for evaluator: orders, revenue, channel mix, kitchen handoff readiness. |
| `square_recent_sales_csv` | — | — | Canonical seeded 6-month sales CSV for marketing-budget reasoning. Read-only. |

### `whatsapp_*` — WhatsApp messaging (4)

| Tool | Required | Optional | Purpose |
|---|---|---|---|
| `whatsapp_send` | **`to`** (E.164), **`message`** (English only) | — | Send a text to a whitelisted simulated customer. |
| `whatsapp_list_threads` | — | — | List recent WhatsApp conversations the team has handled. |
| `whatsapp_register_webhook` | **`url`** (HTTPS, ngrok/Cloudflare Tunnel) | — | Register where the MCP forwards inbound WA events. |
| `whatsapp_inject_inbound` | **`from`**, **`message`** | — | Test-only: inject a simulated inbound WA message. Does NOT message anyone real. |

### `instagram_*` — Instagram DM, comments, posting (8)

| Tool | Required | Optional | Purpose |
|---|---|---|---|
| `instagram_list_dm_threads` | — | — | List the team's recent Instagram DM threads. |
| `instagram_send_dm` | **`threadId`**, **`message`** | — | Send a DM to an IG thread. |
| `instagram_reply_to_comment` | **`commentId`**, **`message`** | — | Reply to a comment under an IG post. |
| `instagram_schedule_post` | **`imageUrl`**, **`caption`** | `scheduledFor` (ISO 8601) | Queue a post for owner approval. Returns `scheduledPostId`. |
| `instagram_publish_post` | **`scheduledPostId`** | — | Publish an approved post. Errors if not yet approved. |
| `instagram_approve_post` | **`scheduledPostId`** | — | Owner-side helper used by the team's Telegram bot when the owner taps "Approve". |
| `instagram_register_webhook` | **`url`** | — | Register inbound IG DM/comment webhook URL. |
| `instagram_inject_dm` | **`threadId`**, **`from`**, **`message`** | — | Test-only: inject a simulated inbound DM. |

### `gb_*` — Google Business profile (4)

| Tool | Required | Optional | Purpose |
|---|---|---|---|
| `gb_list_reviews` | — | — | Recent reviews on the Happy Cake US GMB profile. |
| `gb_simulate_reply` | **`reviewId`**, **`reply`** | — | Record a proposed reply (simulated). Evaluator checks both existence and wording. |
| `gb_simulate_post` | **`content`** | `callToAction{label,url}`, `photoUrl` | Record a proposed GMB post (simulated). |
| `gb_get_metrics` | — | `period` (`last_7_days` \| `last_30_days`) | Sandbox metrics: views, calls, direction requests. |
| `gb_list_simulated_actions` | — | — | Inspect everything the team has recorded in the GMB simulation namespace. |

### `marketing_*` — campaigns, leads, $500/mo loop (10)

| Tool | Required | Optional | Purpose |
|---|---|---|---|
| `marketing_get_budget` | — | — | Returns the constraint: $500/mo budget, $5,000 target effect. |
| `marketing_get_sales_history` | — | — | Anonymized monthly sales history for campaign planning. |
| `marketing_get_margin_by_product` | — | — | Seeded product pricing + margin data for budget allocation. |
| `marketing_create_campaign` | **`name`**, **`channel`** (instagram\|google_local\|whatsapp\|website\|mixed), **`objective`**, **`budgetUsd`**, **`targetAudience`**, **`offer`** | `landingPath` | Create a simulated campaign plan. |
| `marketing_launch_simulated_campaign` | **`campaignId`** | `approvalNote` | Launch a campaign in the simulator; records impressions/clicks/leads/orders estimates. |
| `marketing_get_campaign_metrics` | — | `campaignId` | Read simulated campaign metrics. |
| `marketing_generate_leads` | **`campaignId`** | — | Generate simulated leads for routing. |
| `marketing_route_lead` | **`leadId`**, **`routeTo`** (website\|whatsapp\|instagram\|owner_approval), **`reason`** | — | Record how an agent routed a lead. |
| `marketing_adjust_campaign` | **`campaignId`**, **`adjustment`** | `expectedImpact` | Record an agent adjustment after reading metrics. |
| `marketing_report_to_owner` | — | — | Summarize plan, results, lead routing, and next actions for the owner. |

### `kitchen_*` — production tickets, capacity (8)

| Tool | Required | Optional | Purpose |
|---|---|---|---|
| `kitchen_get_capacity` | — | — | Daily capacity minutes, default lead time, current load. |
| `kitchen_get_menu_constraints` | — | — | Menu-level prep, leadTime, capacity, custom-work constraints. |
| `kitchen_create_ticket` | **`orderId`**, **`customerName`**, **`items[{productId, quantity}]`** | `requestedPickupAt`, `notes` | Create a kitchen production ticket from any order intent. |
| `kitchen_list_tickets` | — | `status` | List team's tickets, optionally filtered by status. |
| `kitchen_accept_ticket` | **`ticketId`** | `note` | Accept a queued ticket if capacity and timing allow. |
| `kitchen_reject_ticket` | **`ticketId`**, **`reason`** | — | Reject when inventory/lead time/capacity makes the promise unsafe. |
| `kitchen_mark_ready` | **`ticketId`** | `pickupNote` | Mark an accepted ticket ready for pickup/handoff. |
| `kitchen_get_production_summary` | — | — | Production summary for evaluator: counts, capacity use, rejections, readiness. |

### `world_*` — deterministic time-compressed scenarios (7)

| Tool | Required | Optional | Purpose |
|---|---|---|---|
| `world_get_scenarios` | — | — | List available scenarios (e.g. `launch-day-revenue-engine`, `weekend-capacity-crunch`). |
| `world_start_scenario` | **`scenarioId`** | `seed` | Start a scenario and reset the team's world timeline. |
| `world_next_event` | — | — | Deliver the next deterministic event in the active scenario. |
| `world_inject_event` | **`channel`**, **`type`**, **`payload`** | `priority` | Inject a custom evaluator/test event without touching real channels. |
| `world_advance_time` | **`minutes`** | — | Advance the scenario clock and preview due events. |
| `world_get_timeline` | — | — | Read the per-team world timeline for debugging/scoring. |
| `world_get_scenario_summary` | — | — | Progress summary: delivered events, channel mix, current minute, remaining events. |

### `evaluator_*` — judging evidence + scoring (6)

| Tool | Required | Optional | Purpose |
|---|---|---|---|
| `evaluator_get_evidence_summary` | — | — | Per-team evidence across world, marketing, POS, kitchen, channels, mcp_audit_log. |
| `evaluator_score_marketing_loop` | — | — | Score the $500 → $5,000 marketing loop. |
| `evaluator_score_pos_kitchen_flow` | — | — | Score Square/POS order flow and kitchen handoff. |
| `evaluator_score_channel_response` | — | — | Score WhatsApp, Instagram, GMB response evidence. |
| `evaluator_score_world_scenario` | — | — | Score deterministic world/scenario execution and MCP audit behavior. |
| `evaluator_generate_team_report` | — | `repoUrl`, `websiteUrl`, `notes` | Combined team evidence report for judges/leaderboard. |

### Raw `tools/list` (canonical schemas)

```json
[
  { "name": "square_list_catalog", "description": "List the simulator-first Happy Cake POS catalog. Works without Square credentials; real Square adapter is server-side opt-in later.", "inputSchema": { "type": "object", "properties": { "limit": { "type": "number" } } } },
  { "name": "square_get_inventory", "description": "Get simulator inventory for catalog variation IDs. Does not require Square env credentials.", "inputSchema": { "type": "object", "properties": { "variationIds": { "type": "array", "items": { "type": "string" } } }, "required": ["variationIds"] } },
  { "name": "square_recent_orders", "description": "Fetch recent simulator POS orders for this team token.", "inputSchema": { "type": "object", "properties": { "sinceISO": { "type": "string" }, "limit": { "type": "number" } } } },
  { "name": "square_create_order", "description": "Create a simulator POS order from website, whatsapp, instagram, walk-in, or agent source. Use kitchen_create_ticket after this for production handoff.", "inputSchema": { "type": "object", "properties": { "items": { "type": "array", "items": { "type": "object", "properties": { "variationId": { "type": "string" }, "quantity": { "type": "number" }, "note": { "type": "string" } }, "required": ["variationId", "quantity"] } }, "source": { "type": "string", "description": "website | whatsapp | instagram | walk-in | agent" }, "customerName": { "type": "string" }, "customerNote": { "type": "string" } }, "required": ["items"] } },
  { "name": "square_update_order_status", "description": "Update simulated POS order status after approval, kitchen handoff, ready, completion, or cancellation.", "inputSchema": { "type": "object", "properties": { "orderId": { "type": "string" }, "status": { "type": "string" }, "note": { "type": "string" } }, "required": ["orderId", "status"] } },
  { "name": "square_get_pos_summary", "description": "Return per-team simulator POS summary for evaluator: orders, revenue, channel mix, and kitchen handoff readiness.", "inputSchema": { "type": "object", "properties": {} } },
  { "name": "square_recent_sales_csv", "description": "Returns canonical seeded 6-month sales CSV for marketing-budget reasoning. Read-only and simulator-safe.", "inputSchema": { "type": "object", "properties": {} } },
  { "name": "whatsapp_send", "description": "Send a text message to a customer on WhatsApp. The customer must be in the team's whitelisted simulated customers list during the hackathon.", "inputSchema": { "type": "object", "properties": { "to": { "type": "string", "description": "E.164 phone number, e.g. +12815551001." }, "message": { "type": "string", "description": "Message body. English only." } }, "required": ["to", "message"] } },
  { "name": "whatsapp_list_threads", "description": "List recent WhatsApp conversations the team has handled.", "inputSchema": { "type": "object", "properties": {} } },
  { "name": "whatsapp_register_webhook", "description": "Register a public URL where this team wants to receive inbound WhatsApp message events. The MCP server will forward incoming events from the shared sandbox to that URL.", "inputSchema": { "type": "object", "properties": { "url": { "type": "string", "description": "A public HTTPS URL on your ngrok or Cloudflare Tunnel." } }, "required": ["url"] } },
  { "name": "whatsapp_inject_inbound", "description": "Test-only: inject a simulated inbound WhatsApp message from a fake customer. Used by the evaluator and by teams to dry-run their own agents. Does NOT actually message anyone.", "inputSchema": { "type": "object", "properties": { "from": { "type": "string", "description": "E.164 phone number of the simulated customer." }, "message": { "type": "string" } }, "required": ["from", "message"] } },
  { "name": "instagram_list_dm_threads", "description": "List the team's recent Instagram DM conversations.", "inputSchema": { "type": "object", "properties": {} } },
  { "name": "instagram_send_dm", "description": "Send a direct message to an Instagram user thread.", "inputSchema": { "type": "object", "properties": { "threadId": { "type": "string" }, "message": { "type": "string" } }, "required": ["threadId", "message"] } },
  { "name": "instagram_reply_to_comment", "description": "Reply to a comment under an Instagram post.", "inputSchema": { "type": "object", "properties": { "commentId": { "type": "string" }, "message": { "type": "string" } }, "required": ["commentId", "message"] } },
  { "name": "instagram_schedule_post", "description": "Queue a post for owner approval. Returns a scheduledPostId. Posts are NEVER published until instagram_publish_post is called by the agent after owner approval.", "inputSchema": { "type": "object", "properties": { "imageUrl": { "type": "string" }, "caption": { "type": "string" }, "scheduledFor": { "type": "string", "description": "ISO 8601 timestamp." } }, "required": ["imageUrl", "caption"] } },
  { "name": "instagram_publish_post", "description": "Publish an approved post from the queue. Reject with an error if the post hasn't been approved by the owner yet.", "inputSchema": { "type": "object", "properties": { "scheduledPostId": { "type": "string" } }, "required": ["scheduledPostId"] } },
  { "name": "instagram_approve_post", "description": "Owner-side helper used by the team's Telegram bot when the owner taps \"Approve\".", "inputSchema": { "type": "object", "properties": { "scheduledPostId": { "type": "string" } }, "required": ["scheduledPostId"] } },
  { "name": "instagram_register_webhook", "description": "Register a public URL where this team wants to receive inbound Instagram DM and comment events. The MCP server forwards simulated events from the shared dev account to that URL.", "inputSchema": { "type": "object", "properties": { "url": { "type": "string", "description": "A public HTTPS URL on your ngrok or Cloudflare Tunnel." } }, "required": ["url"] } },
  { "name": "instagram_inject_dm", "description": "Test-only: inject a simulated inbound DM from a fake follower.", "inputSchema": { "type": "object", "properties": { "threadId": { "type": "string" }, "from": { "type": "string", "description": "IG handle of simulated follower." }, "message": { "type": "string" } }, "required": ["threadId", "from", "message"] } },
  { "name": "gb_list_reviews", "description": "Recent reviews on the Happy Cake US Google Business profile.", "inputSchema": { "type": "object", "properties": {} } },
  { "name": "gb_simulate_reply", "description": "Record a proposed reply to a review. Simulated — does NOT actually post to Google. The evaluator checks both the existence and the wording of the reply.", "inputSchema": { "type": "object", "properties": { "reviewId": { "type": "string" }, "reply": { "type": "string" } }, "required": ["reviewId", "reply"] } },
  { "name": "gb_simulate_post", "description": "Record a proposed Google Business post. Simulated. Used by the team's marketing agent for daily/weekly community updates.", "inputSchema": { "type": "object", "properties": { "content": { "type": "string" }, "callToAction": { "type": "object", "properties": { "label": { "type": "string" }, "url": { "type": "string" } } }, "photoUrl": { "type": "string" } }, "required": ["content"] } },
  { "name": "gb_get_metrics", "description": "Fetch sandbox metrics: views, calls, direction requests for the period.", "inputSchema": { "type": "object", "properties": { "period": { "type": "string", "description": "last_7_days | last_30_days" } } } },
  { "name": "gb_list_simulated_actions", "description": "Inspect everything this team has recorded in the GMB simulation namespace.", "inputSchema": { "type": "object", "properties": {} } },
  { "name": "marketing_get_budget", "description": "Return the Happy Cake monthly marketing constraint and target: make $500/month perform like $5,000.", "inputSchema": { "type": "object", "properties": {} } },
  { "name": "marketing_get_sales_history", "description": "Return anonymized monthly sales history for campaign planning.", "inputSchema": { "type": "object", "properties": {} } },
  { "name": "marketing_get_margin_by_product", "description": "Return seeded product pricing and estimated margin data for budget allocation decisions.", "inputSchema": { "type": "object", "properties": {} } },
  { "name": "marketing_create_campaign", "description": "Create a simulated campaign plan. Records the plan in per-team marketing state.", "inputSchema": { "type": "object", "properties": { "name": { "type": "string" }, "channel": { "type": "string", "description": "instagram | google_local | whatsapp | website | mixed" }, "objective": { "type": "string" }, "budgetUsd": { "type": "number" }, "targetAudience": { "type": "string" }, "offer": { "type": "string" }, "landingPath": { "type": "string" } }, "required": ["name", "channel", "objective", "budgetUsd", "targetAudience", "offer"] } },
  { "name": "marketing_launch_simulated_campaign", "description": "Launch a created campaign inside the simulator and record impressions/clicks/leads/orders estimates.", "inputSchema": { "type": "object", "properties": { "campaignId": { "type": "string" }, "approvalNote": { "type": "string" } }, "required": ["campaignId"] } },
  { "name": "marketing_get_campaign_metrics", "description": "Read simulated campaign metrics for this team.", "inputSchema": { "type": "object", "properties": { "campaignId": { "type": "string" } } } },
  { "name": "marketing_generate_leads", "description": "Generate simulated leads from campaign metrics so teams can route them to website, WhatsApp, Instagram, or owner approval.", "inputSchema": { "type": "object", "properties": { "campaignId": { "type": "string" } }, "required": ["campaignId"] } },
  { "name": "marketing_route_lead", "description": "Record how an agent routed a marketing lead into the sales/customer channel.", "inputSchema": { "type": "object", "properties": { "leadId": { "type": "string" }, "routeTo": { "type": "string", "description": "website | whatsapp | instagram | owner_approval" }, "reason": { "type": "string" } }, "required": ["leadId", "routeTo", "reason"] } },
  { "name": "marketing_adjust_campaign", "description": "Record an agent adjustment after reading campaign metrics.", "inputSchema": { "type": "object", "properties": { "campaignId": { "type": "string" }, "adjustment": { "type": "string" }, "expectedImpact": { "type": "string" } }, "required": ["campaignId", "adjustment"] } },
  { "name": "marketing_report_to_owner", "description": "Summarize campaign plan, simulated results, lead routing, and next actions for the owner.", "inputSchema": { "type": "object", "properties": {} } },
  { "name": "kitchen_get_capacity", "description": "Return simulated kitchen capacity, lead time defaults, and current load summary.", "inputSchema": { "type": "object", "properties": {} } },
  { "name": "kitchen_get_menu_constraints", "description": "Return menu-level preparation, leadTime, capacity, and custom-work constraints.", "inputSchema": { "type": "object", "properties": {} } },
  { "name": "kitchen_create_ticket", "description": "Create a simulated kitchen production ticket from website, WhatsApp, Instagram, or POS order intent.", "inputSchema": { "type": "object", "properties": { "orderId": { "type": "string" }, "customerName": { "type": "string" }, "items": { "type": "array", "items": { "type": "object", "properties": { "productId": { "type": "string" }, "quantity": { "type": "number" } }, "required": ["productId", "quantity"] } }, "requestedPickupAt": { "type": "string" }, "notes": { "type": "string" } }, "required": ["orderId", "customerName", "items"] } },
  { "name": "kitchen_list_tickets", "description": "List simulated kitchen tickets for this team, optionally filtered by status.", "inputSchema": { "type": "object", "properties": { "status": { "type": "string" } } } },
  { "name": "kitchen_accept_ticket", "description": "Accept a queued kitchen ticket if capacity and timing are feasible.", "inputSchema": { "type": "object", "properties": { "ticketId": { "type": "string" }, "note": { "type": "string" } }, "required": ["ticketId"] } },
  { "name": "kitchen_reject_ticket", "description": "Reject a kitchen ticket with a reason when inventory, lead time, or capacity makes it unsafe to promise.", "inputSchema": { "type": "object", "properties": { "ticketId": { "type": "string" }, "reason": { "type": "string" } }, "required": ["ticketId", "reason"] } },
  { "name": "kitchen_mark_ready", "description": "Mark an accepted kitchen ticket ready for pickup or handoff.", "inputSchema": { "type": "object", "properties": { "ticketId": { "type": "string" }, "pickupNote": { "type": "string" } }, "required": ["ticketId"] } },
  { "name": "kitchen_get_production_summary", "description": "Return production summary for evaluator: ticket counts, capacity use, rejections, and readiness.", "inputSchema": { "type": "object", "properties": {} } },
  { "name": "world_get_scenarios", "description": "List deterministic, time-compressed business scenarios available for team/evaluator runs.", "inputSchema": { "type": "object", "properties": {} } },
  { "name": "world_start_scenario", "description": "Start a deterministic time-compressed scenario for this team token and reset its world timeline.", "inputSchema": { "type": "object", "properties": { "scenarioId": { "type": "string" }, "seed": { "type": "number" } }, "required": ["scenarioId"] } },
  { "name": "world_next_event", "description": "Deliver the next deterministic event in the active scenario timeline.", "inputSchema": { "type": "object", "properties": {} } },
  { "name": "world_inject_event", "description": "Inject a custom evaluator/test event into this team timeline without touching real channels.", "inputSchema": { "type": "object", "properties": { "channel": { "type": "string" }, "type": { "type": "string" }, "priority": { "type": "string" }, "payload": { "type": "object" } }, "required": ["channel", "type", "payload"] } },
  { "name": "world_advance_time", "description": "Advance the active scenario clock by simulator minutes and return due events preview.", "inputSchema": { "type": "object", "properties": { "minutes": { "type": "number" } }, "required": ["minutes"] } },
  { "name": "world_get_timeline", "description": "Read the per-team world timeline for debugging and evaluator scoring.", "inputSchema": { "type": "object", "properties": {} } },
  { "name": "world_get_scenario_summary", "description": "Return scenario progress summary: delivered events, channel mix, current minute, and remaining events.", "inputSchema": { "type": "object", "properties": {} } },
  { "name": "evaluator_get_evidence_summary", "description": "Collect per-team simulation evidence across world, marketing, Square/POS, kitchen, channel state, and mcp_audit_log.", "inputSchema": { "type": "object", "properties": {} } },
  { "name": "evaluator_score_marketing_loop", "description": "Score the $500 -> $5,000 marketing loop using simulator evidence.", "inputSchema": { "type": "object", "properties": {} } },
  { "name": "evaluator_score_pos_kitchen_flow", "description": "Score Square/POS order flow and kitchen/production handoff evidence.", "inputSchema": { "type": "object", "properties": {} } },
  { "name": "evaluator_score_channel_response", "description": "Score WhatsApp, Instagram, and Google Business response evidence.", "inputSchema": { "type": "object", "properties": {} } },
  { "name": "evaluator_score_world_scenario", "description": "Score deterministic world/scenario execution and MCP audit behavior.", "inputSchema": { "type": "object", "properties": {} } },
  { "name": "evaluator_generate_team_report", "description": "Generate a combined team evidence report for judges/leaderboard preparation.", "inputSchema": { "type": "object", "properties": { "repoUrl": { "type": "string" }, "websiteUrl": { "type": "string" }, "notes": { "type": "string" } } } }
]
```

## Sample calls

All examples assume you've sourced `.env.local`:

```bash
set -a; source .env.local; set +a
```

### Discovery — `tools/list`

```bash
curl -sS \
  -H "X-Team-Token: $STEPPE_MCP_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
  "$STEPPE_MCP_URL" | jq '.result.tools | length'
# 55
```

### Read-only — `marketing_get_budget`

```bash
curl -sS \
  -H "X-Team-Token: $STEPPE_MCP_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"marketing_get_budget","arguments":{}}}' \
  "$STEPPE_MCP_URL" | jq '.result.content[0].text | fromjson'
```

Verified response (2026-05-09):

```json
{ "monthlyBudgetUsd": 500, "targetEffectUsd": 5000, "challenge": "$500 -> $5,000" }
```

### Read-only — `kitchen_get_capacity`

```bash
curl -sS \
  -H "X-Team-Token: $STEPPE_MCP_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"kitchen_get_capacity","arguments":{}}}' \
  "$STEPPE_MCP_URL" | jq '.result.content[0].text | fromjson'
```

Verified response:

```json
{ "dailyCapacityMinutes": 420, "defaultLeadTimeMinutes": 45, "activePrepMinutes": 0, "remainingCapacityMinutes": 420, "queuedTickets": 0, "acceptedTickets": 0 }
```

### Read-only — `world_get_scenarios`

```bash
curl -sS \
  -H "X-Team-Token: $STEPPE_MCP_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"world_get_scenarios","arguments":{}}}' \
  "$STEPPE_MCP_URL" | jq '.result.content[0].text | fromjson'
```

Returns scenarios including `launch-day-revenue-engine` (480 min, seed 9100510, "1 simulator hour = 10 real minutes") and `weekend-capacity-crunch`.

## Notes & quirks

- **Auth header:** `X-Team-Token`, not `Authorization: Bearer`. The kit ships an `mcpServers` JSON snippet that uses this header verbatim — drop it into the agents' MCP config with the real token.
- **Wire format:** plain JSON-RPC 2.0 over HTTPS POST. No SSE needed despite the `Accept: text/event-stream` hint in the MCP spec — the server returns `content-type: application/json` and a single body.
- **Tool-call envelope:** `params: {name, arguments}`. Successful responses come back as `result.content[0].text` containing **a JSON-encoded string** (note: not a JSON object). Unwrap with `jq '.result.content[0].text | fromjson'` or `json.loads()` in Python before using.
- **Never publish flow:** `instagram_schedule_post` returns a `scheduledPostId`. The post is NOT published until `instagram_publish_post` is called, which requires owner approval routed through `instagram_approve_post`. Treat this as the canonical owner-gate pattern for any judging-visible action.
- **Test-only tools:** `whatsapp_inject_inbound`, `instagram_inject_dm`, and `world_inject_event` are sandbox-only. They do NOT touch real channels. Use them for agent dry-runs and for simulating evaluator events.
- **Evaluator visibility:** the `evaluator_*` family is judge-facing. `evaluator_get_evidence_summary` and `evaluator_generate_team_report` are what we'll call near submission to package what we shipped.
- **Kit prose:** `marketing_create_campaign` → `marketing_launch_simulated_campaign` → `marketing_generate_leads` → `marketing_route_lead` → `marketing_adjust_campaign` → `marketing_report_to_owner` is the demand engine the kit explicitly recommends.
- **Production handoff pattern:** `square_create_order` → `kitchen_create_ticket` (kit explicitly chains them this way).
