# SELF-EVAL.md — official weighted-pass shadow evaluation (T-014)

> One-pass shadow self-eval against the official 7 weighted AI judging passes
> (functional scenario tester, agent-friendliness auditor, on-site assistant
> evaluator, code reviewer, operator simulator, business analyst, and
> innovation/depth spotter — see
> [`HACKATHON-AUDIT.md`](HACKATHON-AUDIT.md) §"Critical finding").
> Honest. Conservative. Each pass cites real files in this repo and real
> evidence in `evidence/`. Numbers are *plausible* — the actual judges
> are independent AI agents we can't simulate exactly. We score where we
> can defend the number.

## Inputs

| Item | Value |
|---|---|
| Eval commit | `a12b5ec` (pre-issue-5 docs sync base) |
| Branch | current fork/worktree |
| Latest committed e2e evidence | [`evidence/e2e-sample.jsonl`](../evidence/e2e-sample.jsonl) — redacted tail from the 20260510T004907Z PASS run; full `evidence/e2e-smoke-*.json` files are local/gitignored by design |
| 4 MCP-loop scores (preview, not the grade) | marketing **100**, pos_kitchen **100**, channels **100**, world **100** — average **100.0** |
| Repo URL on submission | `https://github.com/Jandos22/Arai` |

The four `evaluator_score_*` MCP tools are a **preview** — they are not the
official weighted grade. The seven judging passes read the repo, the website,
and the evidence JSONL. So this self-eval is what we think a reasonable judge
sees, given what's actually committed.

## Methodology — what makes this honest, not a pep talk

- Each pass cites concrete files / line spans / evidence artefacts. No
  hand-waving "we have great architecture" — point at the file.
- Where the four-loop preview is now green, we still keep judge-side scores
  conservative when evidence is thin or requires a human to infer behavior
  from `claude_run` previews instead of explicit outbound-action rows.
- One actionable fix per dim, scoped to fit the May 10 10:00 CT window.
- Each gap traceable to a closure path in
  [`PRODUCTION-PATH.md`](PRODUCTION-PATH.md) where the post-hackathon
  real-adapter swap moves the dial. Hackathon-only fixes are flagged
  separately under "Top 5 final fixes".

## Official weighted score summary

| # | Official pass | Weight | Likely score | Weighted points | Confidence | One-line read |
|---|---|---:|---:|---:|---|---|
| 1 | Functional scenario tester | 20 | **86** | **17.2** | medium | All four preview loops are 100; capacity-aware Square→kitchen evidence is present; channel outbound counters are still worth polishing |
| 2 | Agent-friendliness auditor | 15 | **84** | **12.6** | medium | `/agent.json`, catalog/policies APIs, product JSON-LD, and order deeplinks are shipped; assistant status coverage is thinner |
| 3 | On-site assistant evaluator | 15 | **78** | **11.7** | medium-low | Assistant/custom-order surface exists; no committed transcript proving consultation, complaint, status, and escalation together |
| 4 | Code reviewer | 10 | **86** | **8.6** | high | Plain-Python orchestrator, single MCP chokepoint, scoped agent projects, tests, redaction, and clean env model; no CI |
| 5 | Operator simulator | 15 | **82** | **12.3** | medium | Telegram owner gates, `/capacity`, `/tickets`, and capacity-aware POS flow are documented; screenshots/live reject evidence are thin |
| 6 | Business analyst | 15 | **84** | **12.6** | medium | $500 case is real-data math; ROAS 13.27× simulator; production path concrete; attribution from campaign lead to order is not closed |
| 7 | Innovation/depth spotter | 10 | **76** | **7.6** | medium-low | Agent-readable storefront, scoped MCPs, custom-cake/complaint/allergen gates shipped; growth bonus items remain mostly unbuilt |
| | **Weighted estimate** | **100** | | **82.6 / 100** | | Plausibly 78–87 depending on judge calibration |

Below 80 only if judges heavily discount sandbox previews and require richer
human-visible UX proof. Above 85 if they reward the agent-readable storefront,
owner-gate safety, and production-adapter path as real product surface.

---

## Pass 1 — Functional Scenario Tester (20 pts)

**Likely score: 86 / 100. Confidence: medium.**

What the pass covers: does each channel work end-to-end? Does the order intent
→ kitchen handoff close? Does the marketing loop run? Does the world scenario
produce audit evidence?

### Evidence in repo / logs

- All four MCP loops report a 100/100 preview in the latest committed
  evidence summary: marketing 100, pos_kitchen 100, channels 100, world 100.
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

- **Channel outbound evidence is still indirect.** The committed sample has
  `claude_run.responsePreview` rows and owner-gate rows, but explicit
  `channel_outbound` counters would make the WA/IG/GMB paths easier for a
  judge to verify at a glance.
- **The live e2e sample exercises the accept path, while unit tests cover
  reject/custom/unmapped branches.** Good enough for preview scoring; richer
  live evidence across both branches would be more convincing.
- **No real customer loop ever round-trips.** All inbound is from
  `world_*` injects or `whatsapp_inject_inbound` — there is no real WA
  webhook. We're transparent about this in the brief, but a functional
  scenario tester could mark it.

### One actionable fix (≤30 min)

Patch the channel handlers to write explicit `channel_outbound` evidence rows
whenever the agent returns or triggers a send/reply action. The agent prompts
already have the right tool permissions; this is mostly evidence shape.

---

## Pass 2 — Agent-Friendliness Auditor (15 pts)

**Likely score: 84 / 100. Confidence: medium.**

What the pass covers: can an external agent or judge read the storefront,
catalog, policies, order path, and tool boundaries without scraping a human UI?

### Evidence in repo / logs

- **Agent-readable storefront shipped** via `/agent.json`, `/api/catalog`,
  `/api/policies`, per-product pages, and JSON-LD; these are the surfaces an
  autonomous buyer or evaluator can consume without visual browsing.
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

- **Assistant/status coverage is thinner than catalog coverage.** The static
  storefront APIs are strong; the full consultation/status/escalation behavior
  is less directly visible in committed transcripts.
- **The agent's actual reply text is not in the evidence.** The orchestrator
  logs `claude_run` start/end markers and the dispatcher logs
  `channel_inbound`, but the model's response body isn't preserved in
  `evidence/orchestrator-run-*.jsonl`. A judge reading evidence alone has
  to take it on faith.
- **No injected-error / edge-case scenario in the smoke.** The 12-event
  smoke is "happy path with seeded inbounds" — no out-of-stock, no
  capacity-full, no allergen confusion, no last-minute custom. T-014's
  v1 light red-team was descoped; only the document remains.
- **Agent prompts are static.** They don't read `evidence/` themselves to
  reason about prior context inside a session. (Probably out of scope for
  the brief — flagging because innovation/depth spotters read prompts.)

### One actionable fix (≤20 min)

In `orchestrator/handlers/whatsapp.py:48-49`, capture
`response[:500]` (with token redaction already in `evidence.py`) into a
`channel_outbound` evidence row alongside the existing `claude_run`
markers. This costs <20 lines and gives agent-friendliness judges visible
agent-reply evidence — the single biggest jump in defensibility for the
pass.

---

## Pass 3 — Business Analyst (15 pts)

**Likely score: 84 / 100. Confidence: medium.**

What the pass covers: business value. Would Askhat use this on Monday? Does
the $500→$5K math hold up?

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
  procedure both written (`PRODUCTION-PATH.md:155-261`). This is where
  most demos hand-wave; we don't.
- **Owner UX is Telegram-only as the brief mandates.**
  `orchestrator/telegram_bot.py` + the three dedicated bots in `bots/`
  give the owner a real surface — `/budget`, `/capacity`, `/tickets`,
  inline approve/reject. Listed in `bots/README.md`.

### Risks / gaps

- **Live capacity evidence is still narrow.** The committed e2e sample proves
  an accept decision with capacity math; the reject path is covered by unit
  tests rather than a live sandbox run.
- **Lead routing has logic but no scoring.** Owner sees one lead at a
  time without "this lead is 8/10 vs 4/10" context — would matter at any
  scale (BONUS-PLAN.md:58).
- **No closed-loop attribution from marketing → revenue.** Simulator
  numbers exist but the orchestrator doesn't tie a `marketing_route_lead`
  to a downstream `square_create_order`.

### One actionable fix (≤30 min)

Run one live `weekend-capacity-crunch` or synthetic overloaded Square event
after the current accept-path smoke, then commit a redacted evidence tail that
shows both accept and reject/owner-review behavior.

---

## Pass 4 — On-Site Assistant Evaluator (15 pts)

**Likely score: 78 / 100. Confidence: medium-low.**

What the pass covers: website assistant behavior, customer-facing channel
quality, consultation/custom-order handling, complaint/status/escalation
behavior, and the storefront feel around that assistant.

### Evidence in repo / logs

- **Real cake photos in `website/public/brand/`** — not stock images,
  pulled from the launch kit (`HACKATHON-AUDIT.md:60-67`). Hero, product,
  social, logos.
- **Agent-readable surface shipped.**
  - `/agent.json` — bakery descriptor with capabilities + notSupported,
    contact, endpoints. `website/app/agent.json/route.ts:1-40`.
  - `/api/catalog` — JSON, force-static, with `_orderPath` deeplinks.
    `website/app/api/catalog/route.ts:1-22`.
  - `/api/policies`, `/p/[slug]` per-product page with JSON-LD.
- **LocalBusiness / Bakery JSON-LD + sitemap + robots** — T-011 commit
  `7df1674`. Local SEO checkbox from the bonus plan, shipped.
- **Owner UX in Telegram** with inline keyboards
  (`orchestrator/telegram_bot.py`'s `request_approval` chain — see also
  `agents/sales/CLAUDE.md:213-243` for the JSON the bot consumes).

### Risks / gaps

- **No Lighthouse score on file.** "Mobile performance 🟡 untested" in
  `BONUS-PLAN.md:54`. An on-site assistant evaluator running Lighthouse
  themselves *and* finding a problem we didn't pre-empt is asymmetric
  downside.
- **No screenshots of the Telegram owner flow** anywhere in `docs/`. The
  approve/reject flow is real and good; the judge can't see it without
  setting up a bot.
- **The website has placeholder copy in spots.** Mostly fine, but a
  storefront-eye judge could nit. Specifically, contact phone in
  `website/app/agent.json/route.ts` is a fake `+12815551234`.
- **No on-site assistant test script** — the submission checklist asks
  for "consultation, custom order, complaint, status, escalation"
  (`HACKATHON-AUDIT.md:115-117`). Sales smoke covers parts; a single
  scripted consult-to-resolution sample is missing.

### One actionable fix (≤15 min)

Run Lighthouse mobile against the local dev server and drop the score
plus the screenshot into `docs/UX.md` (or append to README). This is the
top item in `BONUS-PLAN.md:75` (high-leverage low-cost adds, #7) — 15
minutes for a defensible "mobile: 90+" claim, which removes the single
biggest on-site-assistant judge tripwire.

---

## Pass 5 — Code Reviewer (10 pts)

**Likely score: 86 / 100. Confidence: high.**

What the pass covers: system decomposition, visibility, MCP usage, tests,
security hygiene, maintainability, and whether the repo is reviewable.

### Evidence in repo / logs

- **Plain Python, no SDK / LangGraph / CrewAI / n8n.** Routing is a
  literal dict (`orchestrator/main.py:52-78`). `claude -p` is shelled out
  per agent (`orchestrator/claude_runner.py`) — visible, debuggable, no
  framework magic. This is a core brief constraint and we honor it.
- **Single MCP chokepoint.** `orchestrator/mcp_client.py` is the only
  place `STEPPE_MCP_TOKEN` is read; the agent layer never touches the
  network directly. `PRODUCTION-PATH.md:19-40` shows the exact swap
  diagram — this is unusual, judge-visible, and rare among demos that
  mash a real adapter into the agent itself.
- **Per-agent scoped `.mcp.json`.** Each agent gets only the tools it
  needs (`agents/sales/.mcp.json`, `agents/ops/.mcp.json`,
  `agents/marketing/.mcp.json`). Sales explicitly refuses kitchen
  state-machine moves; ops owns those (`agents/sales/CLAUDE.md:67-74`).
- **Routing table is a 6-row dict** with `channel:type` → handler plus
  `channel:*` and `*` fallbacks (`ARCHITECTURE.md:73-81`,
  `orchestrator/dispatcher.py`). Unmatched events drop with an evidence
  row — "missing routes are obvious" is in the docstring.
- **Diagram, event flow, routing table, entry points, and "what's
  shipped"** all in `ARCHITECTURE.md:7-141`. A judge can read it once and
  describe the system back.

### Risks / gaps

- **Agent CLAUDE.md files are long.** `agents/sales/CLAUDE.md` is 280+
  lines. Defensible (six owner-gate triggers, brand voice, JSON shape) —
  but a code reviewer skimming code might flag prompt size as load-bearing
  in a way the architecture diagram doesn't surface.
- **No automated test that the routing table matches the `.mcp.json`
  scopes.** A future commit could add `gb_*` to sales' MCP config without
  the orchestrator catching it.
- **Pre-commit hook installation is manual** (`scripts/git-hooks/pre-commit`
  has a one-line `ln -sf` install in its docstring). Robust enough for
  a solo team; a code reviewer could ask for a `make install-hooks`.

### One actionable fix (≤10 min)

Add a single paragraph to README's "What this is" section explaining
the swap-the-MCP-URL deployment story (already in `PRODUCTION-PATH.md`,
not currently in README). Judges read README first; the architectural
unique-selling-point should not require clicking through.

---

## Pass 6 — Operator Simulator (15 pts)

**Likely score: 82 / 100. Confidence: medium.**

What the pass covers: whether an owner/operator can use the system under a
real business day: approval queues, capacity pressure, ticket visibility,
fallbacks, and failure handling.

### Evidence in repo / logs

- **Telegram owner surface exists** via `orchestrator/telegram_bot.py` and
  the role-specific bots in `bots/`: `/budget`, `/capacity`, `/tickets`, and
  inline approve/reject actions.
- **Capacity-aware POS flow now checks kitchen load before accepting.** The
  committed live evidence proves the accept path; unit tests cover reject,
  custom, and unmapped product branches.
- **Pre-commit hook with three regex patterns** for known leak shapes
  (`scripts/git-hooks/pre-commit:18-26`): `sbc_team_<8+>`, `Bearer
  <20+>`, Telegram bot tokens. Documented allow-list for placeholders.
- **`.env.example` has only placeholders**
  (`.env.example:1-19`). `.gitignore` blocks `.env.local`, `.env.*.local`,
  `*.token`, and the evidence runtime files (with exceptions for
  `*-sample.jsonl` and the schema docs) (`.gitignore:1-23`).
- **Audit trail is structured JSONL** — `evidence/orchestrator-run-*.jsonl`
  with token-redaction baked into `evidence.py`. Schema documented in
  `docs/EVIDENCE-SCHEMA.md`.
- **`scripts/test_website.sh`** smokes the agent-readable surface with
  no token needed — a fresh-clone judge can run it without MCP access.
- **15 unit tests** for `mcp_client`, `dispatcher`, `evidence` —
  deterministic, no network (`ARCHITECTURE.md:120-129`).
- **Pre-submission ritual** documented as a 5-step checklist
  (`SUBMISSION.md:67-86`): `test_website.sh`, `--dry-run`,
  `evaluator_preview.sh`, token-leak grep, push.
- **Deploy + rollback paths written** (`PRODUCTION-PATH.md:155-261`):
  systemd, Tailscale, Cloudflare Tunnel, soft-launch with one product,
  off-switch documented, monitoring spec'd.

### Risks / gaps

- **No screenshots of the Telegram owner flow** anywhere in `docs/`. The
  approve/reject flow is real and good; the judge can't see it without
  setting up a bot.
- **No live monitoring or health-check.** `PRODUCTION-PATH.md:220` says
  "monitoring: orchestrator process alive check + Telegram heartbeat
  every 6h" — spec'd, not built.
- **No CI.** Pre-commit is local. A code-reviewer might dock for "no GitHub
  Actions running tests on every push." Defensible (hackathon scope) but
  worth being explicit about.
- **No `prod_smoke.sh` yet** despite `SUBMISSION.md` referring to one
  (`PRODUCTION-PATH.md:194` "TBW post-hackathon").
- **`evidence/e2e-sample.jsonl` is committed** (the only JSONL allowed
  by `.gitignore:13`). It's redacted via `e2e_smoke.sh:266-272` but a
  paranoid code reviewer will grep for `sbc_team` themselves; we're clean.

### One actionable fix (≤15 min)

Add a simple `scripts/preflight.sh` that runs the 5-step
pre-submission ritual from `SUBMISSION.md:67-86` end-to-end and
exits non-zero if any step fails. Even without CI, this gives the
submitter (Jandos at 09:00 CT) a one-command "ready to ship?" gate
and gives operator/code-review judges a visible artefact to point at.

---

## Pass 7 — Innovation/Depth Spotter (10 pts)

**Likely score: 76 / 100. Confidence: medium-low.**

What the pass covers: bonus-style differentiators, agent reasoning depth,
edge-case handling, and whether the project has a novel product angle beyond
the baseline brief.

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
  (commit `eeabb4f`) — `docs/BONUS-PLAN.md` bucket A items (real
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

- **Bucket C (Growth) is mostly unbuilt** per `BONUS-PLAN.md:58-63`:
  no lead scoring, no referrals, no WhatsApp follow-up cron, no
  upsell logic. Marketing budget optimization is the only green tick
  (and that's T-006, not bonus).
- **No abandoned-orders detection.** ❌ in `BONUS-PLAN.md:51`.
- **Self-eval pipeline (this very document) is partial.** T-014 v1
  spec'd 7 shadow-judge agents + 2 adversarial scenarios; v2 is just
  a hand-written self-eval. Defensible, but a less innovative artefact
  than the spec implied.
- **No referral / repeat-customer flag.** Real bakery's biggest growth
  channel; not in the model.

### One actionable fix (≤30 min)

Ship lead scoring in the marketing agent (`BONUS-PLAN.md:73`, item C5).
Score 0–100 based on channel, intent strength, repeat-customer
inference. Already partially implied by current routing logic — make
it explicit in `marketing_route_lead` evidence. Single 30-min change
that ticks one innovation/depth bonus item with concrete evidence. Bigger win than
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

1. **Capture `whatsapp_send` / `instagram_send_dm` calls as
   `channel_outbound` evidence rows** in `handlers/whatsapp.py` and
   `handlers/instagram.py` (~20 min). Closes the
   "channels=100 but outbound proof is indirect" credibility gap, and lifts
   functional-scenario and innovation/depth defensibility.
2. **Run Lighthouse mobile against the website + commit a screenshot**
   to `docs/` and link from README (~15 min). Removes the biggest
   on-site-assistant tripwire and ticks the `BONUS-PLAN.md` mobile-perf item.
3. **Run one final fresh-clone / preflight pass** (~20 min). Execute the
   no-token website/orchestrator checks, then `scripts/evaluator_preview.sh`
   with `.env.local` populated and confirm the four preview scores still read
   100/100.
4. **Optional: add one live capacity-crunch evidence sample** (~15 min).
   The accept branch is already committed and reject/custom branches are unit
   tested; a live reject/owner-review tail would make the production story
   harder to misread.
5. **Final token-leak scan over full history** per
   `SUBMISSION.md:80`: `git log -p | grep -iE
   '(sbc_team_|Bearer [A-Za-z0-9]{20,})'` should print nothing. Do it
   right before pushing the final commit (~5 min). Single hardest
   failure mode — DQ if a real token slipped in.

Wall-clock for all five: ~70 min. The May 10 09:00 CT dress rehearsal
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
| `evidence/e2e-sample.jsonl` reflects a PASS run with average ≥80 | Score is high enough for full bonus eligibility (`BONUS-PLAN.md:7-14`) |

What to read for the seven official passes, fastest to slowest:

| Official pass | Read this first |
|---|---|
| Functional scenario tester | `evidence/e2e-sample.jsonl` plus a fresh local `bash scripts/e2e_smoke.sh` run if desired |
| Agent-friendliness auditor | `website/app/agent.json/route.ts`, `/api/catalog`, `/api/policies`, and `docs/AGENT-NOTES.md` |
| On-site assistant evaluator | `website/app/assistant/`, `/api/assistant`, and `scripts/test_website.sh` |
| Code reviewer | `docs/ARCHITECTURE.md`, `orchestrator/`, tests, `.env.example`, `.gitignore`, `scripts/git-hooks/pre-commit` |
| Operator simulator | `orchestrator/telegram_bot.py`, `bots/`, `orchestrator/handlers/square.py`, `evidence/e2e-sample.jsonl` |
| Business analyst | `docs/MARKETING.md:147-160` (real MCP chain) + `docs/PRODUCTION-PATH.md` |
| Innovation/depth spotter | `docs/BONUS-PLAN.md` for the inventory; `agents/*/CLAUDE.md` for what's actually wired |

The four `evaluator_score_*` MCP tools are a **preview**, not the
official weighted grade. Treat them as a fast pulse check; the real grade is in
the code, the evidence, and the docs above.

If you want to run the full e2e (5 min wall-clock, drives all four
channels):

```bash
bash scripts/e2e_smoke.sh
```

It self-times-out at 7 min, redacts tokens before writing
`evidence/e2e-sample.jsonl`, and prints PASS/FAIL.

---

*Last revised 2026-05-09. This is a one-pass shadow eval — the actual
seven official passes run independently at 10:00 CT May 10. Numbers above are
honest best-guesses, written to surface fixable gaps, not to predict
the leaderboard.*
