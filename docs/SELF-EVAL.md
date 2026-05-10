# SELF-EVAL.md — official weighted seven-pass shadow evaluation (T-014)

> One-pass shadow self-eval against the official weighted judging passes
> listed on the public hackathon page (see
> [`docs/hackathon/HACKATHON-AUDIT.md`](hackathon/HACKATHON-AUDIT.md) §"Critical finding").
> Honest. Conservative. Each pass cites real files in this repo and real
> evidence in `evidence/`. Numbers are *plausible* — the actual judges
> are independent AI agents we can't simulate exactly. We score where we
> can defend the number.

## Inputs

| Item | Value |
|---|---|
| Eval commit | `0de1948` (`docs(evidence): capture 100.0 e2e smoke pass and marketing run logs`) |
| Branch | `feat/self-eval` (this commit) |
| Latest committed e2e evidence | [`evidence/e2e-sample.jsonl`](../evidence/e2e-sample.jsonl) — redacted tail from the 20260510T020747Z PASS run; full `evidence/e2e-smoke-*.json` files are local/gitignored by design |
| 4 MCP-loop scores (preview, not the grade) | marketing **100**, pos_kitchen **100**, channels **100**, world **100** — average **100.0** |
| Repo URL on submission | `https://github.com/Jandos22/Arai` |

The four `evaluator_score_*` MCP tools are a **preview** — they are not the
seven weighted judging passes. The official judges read the repo, the website,
and the evidence JSONL. So this self-eval is what we think a reasonable judge
sees, given what's actually committed.

## Methodology — what makes this honest, not a pep talk

- Each pass cites concrete files / line spans / evidence artefacts. No
  hand-waving "we have great architecture" — point at the file.
- Where the four-loop preview is now green, we still keep judge-side scores
  conservative when evidence is thin or requires a human to infer behavior
  from `claude_run` previews instead of explicit outbound-action rows.
- One actionable fix per pass, scoped to fit the May 10 10:00 CT window.
- Each gap traceable to a closure path in
  [`PRODUCTION-PATH.md`](PRODUCTION-PATH.md) where the post-hackathon
  real-adapter swap moves the dial. Hackathon-only fixes are flagged
  separately under "Top 5 final fixes".

## Score summary

| # | Official pass | Weight | Likely score | Weighted contribution | Confidence | One-line read |
|---|---|---:|---:|---:|---|---|
| 1 | Functional scenario tester | **20** | **86** | **17.2** | medium | All four loops now preview 100; capacity-aware Square→kitchen evidence is present; channel outbound counters are still worth polishing |
| 2 | Agent-friendliness auditor | **15** | **82** | **12.3** | medium | `/agent.json`, catalog/policy APIs, product JSON-LD, and order-intent path are shipped; richer bot-consumable examples would help |
| 3 | On-site assistant evaluator | **15** | **78** | **11.7** | medium-low | Assistant endpoint and custom-order escalation exist; no recorded consult/status/complaint transcript or owner-flow screenshots |
| 4 | Code reviewer | **10** | **88** | **8.8** | high | Plain-Python orchestrator, single MCP chokepoint, scoped agents, tests, env hygiene, redacted evidence |
| 5 | Operator simulator | **15** | **82** | **12.3** | medium | Telegram owner gate, kitchen capacity decisions, and bot commands are present; live reject/overload evidence is thin |
| 6 | Business analyst | **15** | **88** | **13.2** | medium | $500 case is real-data math (`MARKETING.md:5-44`); ROAS 13.27× simulator; production path concrete |
| 7 | Innovation/depth spotter | **10** | **78** | **7.8** | medium-low | Agent-readable storefront, scoped MCPs, T-013 bonus paths, allergen owner-gate; bucket C growth items mostly unbuilt |
| | **Weighted core total** | **100** | | **83.3** | | Plausibly 79–87 depending on judge calibration, before any bonus |

Bonus functions can add up to +15 points after the 100-point core score.
With a shadow core score above 80, Arai should be eligible for the full
bonus range, but this self-eval does not assign a bonus number.

Below 80 if judges discount sandbox previews heavily or require richer
human-visible proof of owner/customer flows. Above 85 only if the
innovation/depth pass rewards the agent-readable surface as a category in
itself.

---

## Pass 1 — Functional Scenario Tester (20)

**Likely score: 86 / 100. Weighted contribution: 17.2 / 20. Confidence: medium.**

What the pass covers: does each channel work end-to-end? Does the
order intent → kitchen handoff close? Does the marketing loop run?

### Evidence in repo / logs

- All four MCP loops report a 100/100 preview in
  `evidence/e2e-sample.jsonl` (redacted sample from the 20260510T020747Z
  PASS run): marketing 100, pos_kitchen 100, channels 100, world 100.
- Walk-in order **completes the capacity-aware production lifecycle**:
  `square_create_order` → `kitchen_create_ticket` →
  `kitchen_get_capacity` / `kitchen_get_menu_constraints` →
  `square_capacity_decision` → `kitchen_accept_ticket` →
  `kitchen_mark_ready` → `square_update_order_status` — see
  `orchestrator/handlers/square.py:42-111` and the corresponding rows
  preserved in the committed `evidence/e2e-sample.jsonl` tail.
- Marketing demand engine end-to-end chain captured at
  `docs/MARKETING.md:147-160` and reproduced fresh in three independent
  runs (`MARKETING.md:165-313`).
- Smoke runs all four channels in `scripts/e2e_smoke.sh:131-171` (WA inj
  ×2 + IG inj + GMB inj).

### Risks / gaps (be honest)

- **Channel outbound proof is newer than some prose.** The latest sample now
  includes `agent_tool_use` plus `channel_outbound` rows, but older docs and
  smoke commentary may still be less direct than the raw evidence.
- **The live e2e sample exercises the accept path, while unit tests cover
  reject/custom/unmapped branches.** Good enough for preview scoring; richer
  live evidence across both branches would be more convincing.
- **No real customer loop ever round-trips.** All inbound is from
  `world_*` injects or `whatsapp_inject_inbound` — there is no real WA
  webhook. We're transparent about this in the brief, but a functional
  tester could mark it.

### One actionable fix (≤30 min)

Run one live capacity-crunch or overloaded Square event after the current
accept-path smoke, then commit a redacted evidence tail showing both
accept and reject/owner-review behavior.

---

## Pass 2 — Agent-Friendliness Auditor (15)

**Likely score: 82 / 100. Weighted contribution: 12.3 / 15. Confidence: medium.**

What the pass covers: whether the website and repo are easy for an AI agent
to read, navigate, and safely act on.

### Evidence in repo / logs

- **Agent-readable website contract** via `/agent.json`, with capabilities,
  `notSupported`, contact details, and endpoint pointers
  (`website/app/agent.json/route.ts:1-40`).
- **Structured catalog and policy APIs** via `/api/catalog` and
  `/api/policies`, plus per-product pages with JSON-LD. These are better
  surfaces for shopping agents than scraping marketing copy.
- **Order-intent path is explicit**: catalog responses include `_orderPath`
  deeplinks and the website exposes `/order` plus `/api/order-intent`.
- **Agent-friendliness notes are documented** in `docs/AGENT-NOTES.md`,
  so the evaluator has a direct checklist instead of inferring intent from
  implementation details.
- **Five inbound paths** classified agent-side, not by the orchestrator —
  `agents/sales/CLAUDE.md:18-44`: inquiry / order / high-value / complaint
  / custom-cake. Routing is "complaint > custom > owner-gate
  transactional > inquiry" with explicit conservatism.
- **Six owner-gate triggers** with concrete numerical thresholds
  (`agents/sales/CLAUDE.md:76-106`): custom decoration, allergy promise,
  >$80, lead-time window, emotional/complaint, `requiresCustomWork`.
- **Complaint + custom-cake paths shipped** as T-013 — see commit
  `eeabb4f` and the per-`kind` JSON shape at
  `agents/sales/CLAUDE.md:213-243`. `severity: high` is auto-assigned for
  any allergy/illness language.
- **Brand voice is enforced inside the agent prompt**, not bolted on
  afterwards: `agents/sales/CLAUDE.md:108-160` (wordmark, cake-naming
  pattern, emoji rules, refusal style). The marketing agent re-runs of
  `docs/MARKETING.md:165-313` produce three differently-allocated
  campaign briefs without the model reverting to generic ad copy —
  evidence the prompt is doing real work.

### Risks / gaps

- **The contract is static.** It tells agents what exists, but there is no
  formal schema versioning or generated OpenAPI spec for every endpoint.
- **Few example conversations are committed.** An agent auditor can see
  the surfaces, but not a rich set of machine-readable sample tasks and
  expected responses.
- **The agent's actual reply text is not in the evidence.** The orchestrator
  logs `claude_run` start/end markers and the dispatcher logs
  `channel_inbound`, but the model's response body isn't preserved in
  `evidence/orchestrator-run-*.jsonl`. An agent-friendliness auditor reading
  evidence alone has to take it on faith.
- **No injected-error / edge-case scenario in the smoke.** The 12-event
  smoke is "happy path with seeded inbounds" — no out-of-stock, no
  capacity-full, no allergen confusion, no last-minute custom. T-014's
  v1 light red-team was descoped; only the document remains.
- **Agent prompts are static.** They don't read `evidence/` themselves to
  reason about prior context inside a session. (Probably out of scope for
  the brief — flagging because the innovation/depth pass may inspect it.)

### One actionable fix (≤20 min)

Add an `examples` block to `/agent.json` or `docs/AGENT-NOTES.md` covering
consultation, order intent, complaint, and status lookup. This gives the
agent-friendliness auditor concrete task fixtures instead of just endpoint
metadata.

---

## Pass 3 — On-Site Assistant Evaluator (15)

**Likely score: 78 / 100. Weighted contribution: 11.7 / 15. Confidence: medium-low.**

What the pass covers: whether the on-site assistant can handle consultation,
custom order, complaint, status, and escalation flows with useful customer
and owner behavior.

### Evidence in repo / logs

- **On-site assistant route exists** in `website/app/assistant/` with
  backend behavior in `website/app/api/assistant/route.ts`.
- **Website smoke test covers the assistant surface** via
  `scripts/test_website.sh`, including custom-order escalation.
- **Complaint + custom-cake paths shipped** as T-013 — see the per-`kind`
  JSON shape at `agents/sales/CLAUDE.md:213-243`. `severity: high` is
  auto-assigned for allergy/illness language.
- **Owner-gated escalation is explicit** for custom decoration, allergy
  promise, high-value orders, short lead-time orders, and emotional/complaint
  cases (`agents/sales/CLAUDE.md:76-106`).

### Risks / gaps

- **No committed transcript of the full on-site flow.** The evaluator can
  run the script, but the docs do not show a consultation → custom order →
  owner escalation → status follow-up trace.
- **No screenshots of the owner-side Telegram approval flow.** The code is
  present; the evaluator has to set up a bot to see it.
- **Status lookup is less visible than order/custom/complaint handling.**
  It is part of the expected assistant test surface, but not the strongest
  committed evidence.

### One actionable fix (≤30 min)

Commit a short assistant transcript fixture that covers consultation, custom
order, complaint, status, and escalation. Link it from `SUBMISSION.md` so the
on-site assistant evaluator has the exact path in one click.

---

## Pass 4 — Code Reviewer (10)

**Likely score: 88 / 100. Weighted contribution: 8.8 / 10. Confidence: high.**

What the pass covers: repo clarity, implementation quality, testability,
security hygiene, and whether the system is understandable from code.

### Evidence in repo / logs

- **Plain Python, no SDK / LangGraph / CrewAI / n8n.** Routing is a
  literal dict (`orchestrator/main.py:52-78`). `claude -p` is shelled out
  per agent (`orchestrator/claude_runner.py`) — visible, debuggable, no
  framework magic.
- **Single MCP chokepoint.** `orchestrator/mcp_client.py` is the only
  place `STEPPE_MCP_TOKEN` is read; the agent layer never touches the
  sandbox token directly. `PRODUCTION-PATH.md:19-40` shows the real-adapter
  swap path.
- **Per-agent scoped `.mcp.json`.** Each agent gets only the tools it
  needs (`agents/sales/.mcp.json`, `agents/ops/.mcp.json`,
  `agents/marketing/.mcp.json`). Sales explicitly refuses kitchen
  state-machine moves; ops owns those (`agents/sales/CLAUDE.md:67-74`).
- **Tests are deterministic and token-free** for `mcp_client`,
  `dispatcher`, `evidence`, and square capacity decisions
  (`orchestrator/tests/`).
- **Secrets hygiene is documented and enforced locally** via `.env.example`,
  `.gitignore`, token redaction in `orchestrator/evidence.py`, and
  `scripts/git-hooks/pre-commit`.

### Risks / gaps

- **No CI.** Pre-commit is local. A code reviewer might dock for no
  GitHub Actions running tests on every push.
- **No automated test that the routing table matches the `.mcp.json`
  scopes.** A future commit could add a tool to the wrong agent config
  without the orchestrator catching it.
- **Pre-commit hook installation is manual** (`scripts/git-hooks/pre-commit`
  has a one-line `ln -sf` install in its docstring). Robust enough for
  a solo team; still not a full repository bootstrap.

### One actionable fix (≤15 min)

Add a simple `scripts/preflight.sh` that runs the no-token website test,
orchestrator dry-run, and leak scan. This gives the code reviewer one
command to validate the repo's intended quality gate.

---

## Pass 5 — Operator Simulator (15)

**Likely score: 82 / 100. Weighted contribution: 12.3 / 15. Confidence: medium.**

What the pass covers: whether the system helps the bakery operator make
safe, timely decisions during a live business day.

### Evidence in repo / logs

- **Owner UX is Telegram-only as the brief mandates.**
  `orchestrator/telegram_bot.py` + the three dedicated bots in `bots/`
  give the owner a real surface — `/budget`, `/capacity`, `/tickets`,
  inline approve/reject. Listed in `bots/README.md`.
- **Capacity-aware Square→kitchen handoff is implemented.**
  `orchestrator/handlers/square.py` checks `kitchen_get_capacity` and
  `kitchen_get_menu_constraints`, writes a `square_capacity_decision` row,
  then accepts/marks ready or routes rejection/owner review.
- **Kitchen owner approval is modeled** through
  `ticket_pending_owner_approval` routing and `kitchen.handle`.
- **World scenario loop matches evaluator mechanics**:
  `world_start_scenario` / `world_next_event` are the same primitives used
  in live preview and e2e smoke.
- **Evidence is operator-readable**: JSONL rows expose channel inbounds,
  capacity decisions, MCP calls, approval requests, and scenario summaries.

### Risks / gaps

- **Live capacity evidence is still narrow.** The committed e2e sample proves
  an accept decision with capacity math; the reject path is covered by unit
  tests rather than a live sandbox run.
- **No screenshots of the Telegram owner flow** anywhere in `docs/`. The
  approve/reject flow is real and useful; the evaluator can't see it without
  setting up a bot.
- **No health-check heartbeat is built.** `PRODUCTION-PATH.md` specifies
  the operating model, but the live monitor is post-hackathon work.

### One actionable fix (≤15 min)

Run one live `weekend-capacity-crunch` or synthetic overloaded Square event
after the current accept-path smoke, then commit a redacted evidence tail that
shows both accept and reject/owner-review behavior.

---

## Pass 6 — Business Analyst (15)

**Likely score: 88 / 100. Weighted contribution: 13.2 / 15. Confidence: medium.**

What the pass covers: whether the business case is numerically defensible and
useful to Askhat, not just technically plausible.

### Evidence in repo / logs

- **$500 → $5K case is real data, not back-of-envelope.** Six months of
  Square sales pulled via `marketing_get_sales_history`, cross-checked
  with `square_recent_sales_csv`; channel split justified by
  `gb_get_metrics(period:"last_30_days")` (87 directions, 41 calls, 96
  website clicks in 30d). See `docs/MARKETING.md:5-44` and the Methodology
  note at `MARKETING.md:314-327`.
- **Three independent marketing runs** all clear 10× ROAS (13.27×,
  13.5×, 13.6×) using *different* allocations — the agent produces
  defensible math under varied triggers, not one rehearsed answer.
  `MARKETING.md:165-313`.
- **Production path is concrete.** Real-API equivalents tabled tool by
  tool (`PRODUCTION-PATH.md:44-72`); critical-path lead time identified
  (WhatsApp Business verification, 3–5 days); rotation cadence per
  vendor (`PRODUCTION-PATH.md:104-110`); deploy steps and rollback
  procedure both written (`PRODUCTION-PATH.md:155-261`).
- **Business-impact hypothesis is visible in submission docs** and links
  directly to the marketing evidence rather than only describing product
  features.
- **Capacity-aware order acceptance supports the business case** by avoiding
  overpromising during demand spikes, not just generating leads.

### Risks / gaps

- **Lead routing has logic but no scoring.** Owner sees one lead at a
  time without "this lead is 8/10 vs 4/10" context — would matter at any
  scale (`docs/hackathon/BONUS-PLAN.md:58`).
- **No closed-loop attribution from marketing → revenue.** Simulator
  numbers exist but the orchestrator doesn't tie a `marketing_route_lead`
  to a downstream `square_create_order`.
- **The $5K target is simulator-backed, not real post-launch revenue.**
  That is expected for the hackathon, but should be stated plainly.
- **The business analyst may want a clearer CAC/payback table.** The raw
  campaign evidence is strong; a one-screen summary would reduce reading
  burden.

### One actionable fix (≤30 min)

Ship lead scoring in the marketing agent (`docs/hackathon/BONUS-PLAN.md:73`, item C5).
Score 0–100 based on channel, intent strength, repeat-customer inference,
and order urgency so the business analyst can see prioritization logic.

---

## Pass 7 — Innovation and Depth Spotter (10)

**Likely score: 78 / 100. Weighted contribution: 7.8 / 10. Confidence: medium-low.**

What the pass covers: differentiators beyond the baseline brief, plus depth
of reasoning and edge-case handling.

### Evidence in repo / logs

- **`/agent.json` + agent-readable storefront** — not asked for, shipped.
  `website/app/agent.json/route.ts`, `docs/AGENT-NOTES.md`. This is the
  kind of thing a future Claude / GPT shopping agent would *actually*
  use to order from the bakery — concrete, machine-readable contract
  with `capabilities` and `notSupported`.
- **Per-agent scoped MCP configs** — sibling agents with non-overlapping
  tool sets (`agents/sales/.mcp.json`, `agents/ops/.mcp.json`,
  `agents/marketing/.mcp.json`). Three Telegram bots in `bots/` give
  each agent its own owner-chat surface.
- **T-013 complaint + custom-cake bonus paths shipped**
  (commit `eeabb4f`) — `docs/hackathon/BONUS-PLAN.md` bucket A items (real
  business pain) covered for both. Allergen routing always
  owner-gated, severity field auto-set on illness language.
- **Kitchen-aware allergen flag** — sales agent refuses to promise
  allergen-safe even when customer asks directly
  (`agents/sales/CLAUDE.md:88-90`). Rare in demos.
- **LocalBusiness/Bakery JSON-LD + Open Graph + sitemap + robots**
  (T-011, commit `7df1674`).
- **The orchestrator's `world_*` loop is the same loop the evaluator
  drives** — what we test in dev = what's judged
  (`ARCHITECTURE.md:1-6`). Innovation in the *evaluation* surface, not
  just the product.

### Risks / gaps

- **Bucket C (Growth) is mostly unbuilt** per `docs/hackathon/BONUS-PLAN.md:58-63`:
  no lead scoring, no referrals, no WhatsApp follow-up cron, no
  upsell logic. Marketing budget optimization is the only green tick
  (and that's T-006, not bonus).
- **No abandoned-orders detection.** ❌ in `docs/hackathon/BONUS-PLAN.md:51`.
- **Self-eval pipeline (this very document) is partial.** T-014 v1
  spec'd 7 shadow-judge agents + 2 adversarial scenarios; v2 is just
  a hand-written self-eval. Defensible, but a less innovative artefact
  than the spec implied.
- **No referral / repeat-customer flag.** Real bakery's biggest growth
  channel; not in the model.

### One actionable fix (≤30 min)

Ship lead scoring in the marketing agent (`docs/hackathon/BONUS-PLAN.md:73`, item C5).
Score 0–100 based on channel, intent strength, repeat-customer
inference. Already partially implied by current routing logic — make
it explicit in `marketing_route_lead` evidence. Single 30-min change
that ticks one innovation/depth item with concrete evidence. Bigger win than
adding any new doc.

---

## Why POS/kitchen preview is now 100/100

The earlier self-eval was written after the first Square fix but before the
capacity-aware handoff landed. At that point the docs only described the basic
seeded walk-in order lifecycle:

```
square_create_order → kitchen_create_ticket → kitchen_accept_ticket
→ kitchen_mark_ready → square_update_order_status
```

The later fix added the missing production decision loop in
`orchestrator/handlers/square.py`: after `kitchen_create_ticket`, the handler
now reads `kitchen_get_capacity` and `kitchen_get_menu_constraints`, computes
required prep minutes, writes a `square_capacity_decision` row, and then either
accepts/marks ready or routes a rejection/owner-review path.

The latest committed `evidence/e2e-sample.jsonl` shows the green accept path:
6 honey-cake slices require 18 prep minutes, capacity has 402 minutes
remaining, the ticket is accepted, marked ready, and the Square order is moved
to `ready`. `docs/SUBMISSION.md` records the corresponding preview result:
M:100 / POS:100 / Ch:100 / W:100.

The remaining honesty note is narrow: the committed live e2e sample shows the
accept branch, while `orchestrator/tests/test_square_capacity.py` covers the
reject/custom/unmapped branches. That is enough for the preview score, but a
second redacted live sample from a capacity-crunch scenario would make the
production story even easier to verify.

## Top 5 final fixes before submission

In rank order by points-per-minute:

1. **Add one live capacity-crunch evidence sample** (~15 min). The accept
   branch is already committed and reject/custom branches are unit tested; a
   live reject/owner-review tail would make the production story harder to
   misread.
2. **Run Lighthouse mobile against the website + commit a screenshot**
   to `docs/` and link from README (~15 min). Removes the biggest
   on-site assistant / storefront tripwire and ticks the `docs/hackathon/BONUS-PLAN.md`
   mobile-perf item.
3. **Run one final fresh-clone / preflight pass** (~20 min). Execute the
   no-token website/orchestrator checks, then `scripts/evaluator_preview.sh`
   with `.env.local` populated and confirm the four preview scores still read
   100/100.
4. **Final token-leak scan over full history** per
   `SUBMISSION.md`: `bash scripts/secret_scan.sh` should print
   `clean`. Do it right before pushing the final commit (~5 min).
   Single hardest failure mode — DQ if a real token slipped in.

Wall-clock for all four: ~55 min. The May 10 09:00 CT dress rehearsal
in `SUBMISSION.md:38` is the hard gate.

## Judge readme — verify the core vertical slice in 5 minutes

> Reading this section as a judge — here's the shortest path to verify
> we built what we claim.

```bash
# 0. Clone
git clone https://github.com/Jandos22/Arai && cd Arai

# 1. Static surface — no token needed (~30s)
bash scripts/test_website.sh

# 2. Orchestrator wiring — no token needed (~5s)
cd orchestrator && uv venv --python 3.12 .venv \
  && uv pip install -r requirements.txt \
  && PYTHONPATH=.. .venv/bin/python -m orchestrator.main --dry-run
cd ..

# 3. Live evaluator preview — needs your team token in .env.local (~30s)
cp .env.example .env.local
# (paste STEPPE_MCP_TOKEN from your kit)
bash scripts/evaluator_preview.sh
```

What you're verifying:

| You see this | It means |
|---|---|
| `[1/7]` … `[7/7] PASS` | All four MCP scoring loops returned a non-error response |
| `marketing : 100`, `pos_kitchen : 100`, `channels : 100`, `world : 100` | The four-loop preview matches our self-eval inputs |
| `evidence/e2e-sample.jsonl` reflects a PASS run with average ≥80 | The preview signal is strong enough to justify reading the weighted self-eval |

What to read for the seven official passes, fastest to slowest:

| Official pass | Read this first |
|---|---|
| Functional scenario tester | `evidence/e2e-sample.jsonl` plus a fresh local `bash scripts/e2e_smoke.sh` run if desired |
| Agent-friendliness auditor | `website/app/agent.json/route.ts`, `/api/catalog`, `/api/policies`, `docs/AGENT-NOTES.md` |
| On-site assistant evaluator | `website/app/assistant/`, `website/app/api/assistant/route.ts`, `scripts/test_website.sh` |
| Code reviewer | `docs/ARCHITECTURE.md`, `orchestrator/tests/`, `.env.example`, `scripts/git-hooks/pre-commit` |
| Operator simulator | `orchestrator/telegram_bot.py`, `bots/README.md`, `orchestrator/handlers/square.py` |
| Business analyst | `docs/MARKETING.md:147-160` (real MCP chain) + `docs/PRODUCTION-PATH.md` |
| Innovation/depth spotter | `docs/hackathon/BONUS-PLAN.md` for the inventory; `agents/*/CLAUDE.md` for what's actually wired |

The four `evaluator_score_*` MCP tools are a **preview**, not the
seven weighted judging passes. Treat them as a fast pulse check; the real
grade is in the code, the evidence, and the docs above.

If you want to run the full e2e (5 min wall-clock, drives all four
channels):

```bash
bash scripts/e2e_smoke.sh
```

It self-times-out at 7 min, redacts tokens before writing
`evidence/e2e-sample.jsonl`, and prints PASS/FAIL.

---

*Last revised 2026-05-09. This is a one-pass shadow eval — the official
weighted passes run independently at 10:00 CT May 10. Numbers above are
honest best-guesses, written to surface fixable gaps, not to predict
the leaderboard.*
