# Mission — Marketing Agent run

You are running headless as the HappyCake Marketing Agent. Your `CLAUDE.md`
in this folder is your role contract; read it now if you haven't.

This single run must:

1. **Read the inputs** — call each of these once, in order, and remember the
   numbers you need for the plan:

   - `mcp__happycake__marketing_get_budget`
   - `mcp__happycake__marketing_get_sales_history`
   - `mcp__happycake__marketing_get_margin_by_product`
   - `mcp__happycake__square_recent_sales_csv`
   - `mcp__happycake__gb_get_metrics` with `{"period":"last_30_days"}`

2. **Decide a budget split** across channels (`instagram`, `google_local`,
   `whatsapp`, `website`, `mixed`). Total must equal $500. Show the math —
   weight margin × historical conversion × channel intent (use the GMB
   metrics for local intent). Boring + cited beats clever + opaque.

3. **Create exactly 3 campaigns** with
   `mcp__happycake__marketing_create_campaign`. Constraints:

   - Distinct channels.
   - At least one explicitly targets a family / celebration moment
     (birthday, anniversary, weekend dessert, school event, etc.).
   - Names and offers in HappyCake brand voice (read
     `../../docs/brand/HCU_BRANDBOOK.md` sections 1–3 + 5 if you need a
     refresher). No "luxury", no "artisanal", no "limited offer!!!", no
     emoji storms. Cake names in quotes after the word *cake*.
   - `targetAudience` must reference the audience profile (women 25–65,
     Sugar Land / Houston families).
   - Customer-facing copy lines should close with: *Order on the site at
     happycake.us or send a message on WhatsApp.*

4. **For each campaign, in this order**:

   a. `mcp__happycake__marketing_launch_simulated_campaign`
   b. `mcp__happycake__marketing_generate_leads`
   c. For **every** lead returned, call
      `mcp__happycake__marketing_route_lead` with one of
      `website | whatsapp | instagram | owner_approval` and a one-sentence
      `reason` that names the lead's signal (intent, channel of origin,
      time-of-day, etc.). High-value or unusual leads → `owner_approval`.
   d. `mcp__happycake__marketing_get_campaign_metrics`
   e. `mcp__happycake__marketing_adjust_campaign` once, with a justified
      `adjustment` string and an `expectedImpact` string.

5. **Report** with `mcp__happycake__marketing_report_to_owner`. Capture the
   response verbatim — you will paste it into the doc.

6. **Write `docs/MARKETING.md`** (use the `Write` tool, path
   `/Users/jandos/dev/Arai/docs/MARKETING.md`). The file is the $500-case
   write-up the hackathon brief explicitly asks for. Required sections, in
   this order:

   - **`# MARKETING.md — the $500 case for HappyCake`**
   - `## Inputs` — bullet list, every number cited from a tool you called.
   - `## Budget allocation` — Markdown table with columns
     `Channel | $ | Why this channel | Expected leads`. Below the table,
     a 2–4 sentence math walkthrough.
   - `## Campaign briefs` — three subsections (one per campaign), each with
     name, channel, audience, offer, sample copy (≤4 lines, brand voice).
   - `## Simulated results` — table per campaign of impressions / clicks /
     leads / orders, with the `campaignId` returned by the sandbox.
   - `## Lead routing` — count per `routeTo` plus a 2-sentence narrative on
     how you decided.
   - `## Adjustments` — one row per campaign: what changed, why, expected
     impact (verbatim from the tool response).
   - `## Owner report` — paste the `marketing_report_to_owner` response.
   - `## If this were real next month` — one paragraph. What you would do
     differently. Mention that re-running this script creates duplicate
     sandbox campaigns — idempotency is intentionally not enforced for the
     demo.
   - `## Methodology note` — one short paragraph: which sandbox tools were
     called, that all numbers are simulator outputs, and that the run is
     reproducible from `agents/marketing/run.sh` plus `.env.local`.

7. **Final reply** to me (stdout):

   - One short paragraph (1–2 sentences) summarising what shipped: number
     of campaigns, leads routed, owner-report headline.
   - Then the literal evidence block, exactly:

     ```
     --- EVIDENCE BEGIN ---
     {"ts":"<ISO-8601 UTC>","tool":"<tool_name>","args_summary":"<short>","result_summary":"<short>","decision_rationale":"<short>"}
     ... one JSON line per MCP call you made, in order ...
     --- EVIDENCE END ---
     ```

   The wrapper script greps between those markers to populate
   `evidence/marketing.jsonl`. Keep each line a single valid JSON object,
   no trailing commas, no extra prose between markers.

## Hard rules during this run

- Do not call any tool outside the allowed list (see CLAUDE.md).
- Do not invent product facts, prices, or margins. If `marketing_get_margin_by_product`
  didn't return it, don't cite it.
- Total campaign `budgetUsd` must equal **500**.
- Wordmark is **HappyCake** — one word.
- Never echo the `STEPPE_MCP_TOKEN` or any auth header into the doc, the
  evidence block, or stdout.

Begin now. Use parallel tool calls only when calls are independent (the five
read calls in step 1 are independent → batch them).
