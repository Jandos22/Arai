---
name: arai-self-eval
description: |
  Arai-specific: run the seven-pass weighted shadow self-eval against the
  current repo. Spawns 7 parallel judge agents aligned to the official
  hackathon rubric, optionally adds a 3-persona customer red-team, runs a
  reconciler that catches contradictions, and writes a timestamped report
  under evidence/. Use before submission, after a non-trivial change, or
  when the user asks "where do we stand", "score the repo", "run self-eval",
  or "shadow judges". Project-scoped: not loaded outside the Arai repo.
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
  - Agent
  - AskUserQuestion
  - Skill
triggers:
  - self eval
  - self-eval
  - shadow judges
  - score the repo
  - arai self eval
  - run self eval
  - where do we stand
---

# /arai-self-eval — 7-pass weighted shadow self-eval, aligned to the official rubric

You are running the **leaderboard-aligned shadow eval** for Arai. The official
hackathon judges grade seven weighted passes (Functional 20, Agent-friendliness
15, On-site assistant 15, Code reviewer 10, Operator simulator 15, Business
analyst 15, Innovation/depth 10). This skill mirrors that exact rubric using
parallel sub-agents so the user gets a defensible, re-runnable score with
concrete fix recommendations.

## What this rebuilds vs. the original T-014 design

T-014 was descoped to a hand-written `docs/SELF-EVAL.md`. This skill ships the
agentic version with six concrete improvements:

1. **Weights match the official rubric** (20/15/15/10/15/15/10), not equal 1/7.
2. **Brand-grounded.** Every judge prelude-reads `BRAND_FACTS.md` so it doesn't
   ding the agents for following actual Happy Cake conventions.
3. **Citations are quote+lines, validated.** A judge that cites
   `orchestrator/handlers/square.py:42-58` must include a literal quoted snippet;
   the runner greps the file and fails the citation if the quote is absent.
4. **Live MCP reconciliation.** Judges that overlap an `evaluator_score_*`
   preview tool call it and reconcile their narrative score against the
   preview number.
5. **3-persona customer red-team** — Maira (Kazakh / Nauryz / allergen),
   Jen (Sugar Land mom / last-minute), DeShawn (B2B office order). Real
   customer types from `BRAND_FACTS.md`, not abstract scenarios.
6. **Reconciler pass.** A final agent reads all 7 + 3 outputs and surfaces
   contradictions (e.g. "Functional cites strong Square handoff but Code
   reviewer flags missing tests for the same handler") before the score is
   committed.

## Hard rules (do not violate)

- **No fabricated citations.** Every `evidence_pointers[]` row needs `path`,
  `lines` (e.g. `42-58`), and `quote` (a short literal substring). Validation
  step (Phase 5) fails any citation whose quote isn't in the file at the line
  range. Hallucinated citations zero out the dim's evidence credit.
- **No reading outside the scope a judge is given.** Each judge's reading
  envelope is listed below. Don't let a judge wander into other dims —
  that's what the reconciler is for.
- **Brand prelude is mandatory.** Every spawned judge prompt starts with
  "Read `.claude/skills/arai-self-eval/BRAND_FACTS.md` first."
- **No new artefacts in `docs/` without user confirm.** Default writes go to
  `evidence/self-eval-<ts>.{json,md}`. Updating `docs/SELF-EVAL.md` is opt-in
  via Phase 6.
- **Owner UX is Telegram-only.** Any judge recommendation that proposes
  email/web-dashboard owner UI is a recommendation error and the reconciler
  must flag it.

---

## Phase 0 — Pre-flight (no LLM cost)

Run these checks in parallel and abort with a clean error if any fails.

```bash
# Token loaded
source scripts/load_env.sh && arai_load_env "$PWD"
[ ${#STEPPE_MCP_TOKEN} -eq 41 ] || { echo "STEPPE_MCP_TOKEN not loaded"; exit 1; }

# Fresh evidence (smoke ran in last 24h)
latest=$(ls -t evidence/orchestrator-*.jsonl 2>/dev/null | head -1)
[ -n "$latest" ] || { echo "no orchestrator evidence — run scripts/e2e_smoke.sh first"; exit 1; }
test "$(find "$latest" -mtime -1)" || echo "WARN: latest evidence older than 24h"

# Repo clean enough to score
git status --short | head -20  # informational
```

Then run the 4-loop preview to seed Functional / Operator / Business judges
with the live MCP signal:

```bash
bash scripts/evaluator_preview.sh
preview="$(ls -t evidence/evaluator-preview-*.json | head -1)"
echo "preview=$preview"  # judges 1, 5, 6 will read this
```

If the preview shows any loop < 80, surface it to the user before continuing —
the bonus gate is core ≥80.

### Orchestrator lifecycle (only when Phase 2 personas will run)

Phase 2 needs a running orchestrator so injected inbounds get dispatched to
`agents/sales/` via `claude -p` and the resulting transcript lands in
`evidence/orchestrator-*.jsonl`. If the user passed `--fast` or explicitly
said "skip personas", **skip this whole subsection** — leave the orchestrator
state alone.

Otherwise:

```bash
PID_FILE="/tmp/arai-self-eval-orch.pid"
OWN_FILE="/tmp/arai-self-eval-started-orch"
ORCH_LOG="/tmp/arai-self-eval-orch.log"

# Opportunistic cleanup of leaked process from a prior crashed run
if [ -f "$OWN_FILE" ] && [ -f "$PID_FILE" ]; then
  prev_pid=$(cat "$PID_FILE" 2>/dev/null || echo "")
  if [ -n "$prev_pid" ] && ! kill -0 "$prev_pid" 2>/dev/null; then
    rm -f "$PID_FILE" "$OWN_FILE"
  fi
fi

# Detect existing orchestrator (user-started or ours-still-alive)
if pgrep -f "orchestrator\.main" >/dev/null 2>&1; then
  echo "orchestrator: already running, leaving it alone"
  # Do NOT touch OWN_FILE — we don't own it
else
  echo "orchestrator: starting (will be shut down at end of skill)"
  nohup python -m orchestrator.main >"$ORCH_LOG" 2>&1 &
  echo $! > "$PID_FILE"
  touch "$OWN_FILE"   # marker: this skill owns the process
  # Wait for boot — orchestrator typically logs "scenario_summary" or
  # "scenario_runner" within 3-5s. Cap the wait at 15s.
  for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
    sleep 1
    if grep -q -E "(scenario_runner|world_next_event|orchestrator ready)" "$ORCH_LOG" 2>/dev/null; then
      echo "orchestrator: booted after ${i}s"
      break
    fi
    if ! kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "orchestrator: died during boot (see $ORCH_LOG)"
      rm -f "$PID_FILE" "$OWN_FILE"
      break
    fi
  done
fi
```

The `OWN_FILE` marker is the only thing that authorizes Phase 7 to kill the
process. If the user already had the orchestrator running, we leave it
running at the end too.

---

## Phase 1 — Spawn the 7 weighted judges (parallel)

Use the `Agent` tool with `subagent_type: general-purpose` for each judge.
**Send all 7 in a single message with 7 parallel tool calls** so they run
concurrently. Each agent's prompt template is below; substitute the values
in `{{}}` per-judge.

### Per-judge prompt template

```
You are a shadow judge for the Steppe Business Club hackathon.
Score the Arai repo on the **{{DIM}}** dimension (weight {{WEIGHT}}/100).

Context (read these in order, then score):
1. .claude/skills/arai-self-eval/BRAND_FACTS.md  (anti-fabrication ground truth)
2. .claude/skills/arai-self-eval/SKILL.md §"Per-judge rubric — {{DIM}}"
3. Your reading envelope: {{SCOPE}}
4. {{LIVE_MCP_NOTE}}

Output exactly one JSON object to stdout — nothing else, no prose, no fences:

{
  "dimension": "{{DIM}}",
  "weight": {{WEIGHT}},
  "score_0_100": <int>,
  "weighted": <score_0_100 * weight / 100>,
  "confidence": "high|medium|low",
  "rationale": "<3-5 sentence summary of WHY this score, citing the rubric criteria>",
  "criteria": [
    {"name": "<criterion>", "score_0_25": <int>, "note": "<one line>"}
    // 4 criteria, sum to score_0_100
  ],
  "evidence_pointers": [
    {"path": "<repo-relative path>", "lines": "<start-end>", "quote": "<literal substring present in the file>"}
    // 3-6 pointers, each must be verifiable via grep
  ],
  "weaknesses": ["<concrete gap 1>", "<concrete gap 2>", "<concrete gap 3>"],
  "recommendations": [
    {"fix": "<≤30-min change>", "expected_score_delta": <int>, "where": "<file or area>"}
    // 2-4 fixes, ranked by points-per-minute
  ]
}

Hard rules:
- Every quote must be a literal substring in the cited file. Don't paraphrase.
- Don't read files outside SCOPE — the reconciler covers cross-dim issues.
- If you can't find evidence for a criterion, score it low and say so. Don't
  invent.
- Brand grounding wins ties. A reply that names "Cloud Cake" beats one that
  says "vanilla cake" of equivalent functional quality.
```

### The 7 judges (dispatch table)

| # | DIM | WEIGHT | SCOPE (reading envelope) | LIVE MCP |
|---|---|---:|---|---|
| 1 | functional | 20 | `evidence/orchestrator-*.jsonl` (latest run only), `evidence/e2e-sample.jsonl`, `scripts/e2e_smoke.sh`, `orchestrator/dispatcher.py`, `orchestrator/handlers/`, `orchestrator/scenario.py` | "Read `evidence/evaluator-preview-*.json` (latest). Reconcile your score with `pos_kitchen`, `channels`, `world` previews — if you score below the preview, justify why; if above, justify what evidence the preview misses." |
| 2 | agent-friendly | 15 | `website/app/agent.json/`, `website/app/api/catalog/`, `website/app/api/policies/`, `website/app/products/`, `website/app/order/`, `docs/AGENT-NOTES.md` | "No live MCP. Score the static contract surface only." |
| 3 | on-site-assistant | 15 | `website/app/assistant/`, `website/app/api/assistant/`, `agents/sales/PROMPTS/`, `agents/sales/CLAUDE.md`, `scripts/test_website.sh` | "No live MCP. Look for committed transcript fixtures and the 5 flows: consultation, custom-cake, complaint, status, escalation." |
| 4 | code-reviewer | 10 | `orchestrator/main.py`, `orchestrator/mcp_client.py`, `orchestrator/claude_runner.py`, `orchestrator/evidence.py`, `orchestrator/tests/`, `agents/*/.mcp.json`, `.env.example`, `.gitignore`, `scripts/git-hooks/` | "No live MCP. Verify there's no SDK / LangGraph / CrewAI / n8n in deps." |
| 5 | operator-sim | 15 | `orchestrator/telegram_bot.py`, `bots/`, `orchestrator/handlers/square.py`, `orchestrator/handlers/owner_msg.py` (if present), `agents/ops/CLAUDE.md`, `agents/ops/policies/` | "Read `evidence/evaluator-preview-*.json` (latest). Reconcile with `pos_kitchen`. Check for both accept and reject branches in evidence." |
| 6 | business-analyst | 15 | `docs/MARKETING.md`, `docs/PRODUCTION-PATH.md`, `evidence/marketing-*.jsonl`, `evidence/marketing-sample.jsonl`, `agents/marketing/CLAUDE.md` | "Read `evidence/evaluator-preview-*.json` (latest). Reconcile with `marketing` preview. Verify the $500→$5K case is real-data math, not back-of-envelope." |
| 7 | innovation | 10 | `docs/BONUS-PLAN.md`, `docs/SUBMISSION.md`, `website/app/agent.json/route.ts`, `agents/sales/CLAUDE.md` (allergen owner-gate), `agents/*/.mcp.json` (scoped tools), `tasks/DONE/T-013-*.md` | "Score the *concept* of self-eval here, not the existence of this skill (avoid double-counting)." |

### Per-judge rubric — criteria each judge scores 0–25

#### 1. functional (20)
- **Channel coverage** — WA + IG + website + GMB all exercised in latest evidence
- **Order intent → kitchen** — capacity-aware, both accept and reject branches present
- **Marketing loop** — lead generation + routing + spend math, ≥10× ROAS
- **Failure handling** — at least one out-of-stock, capacity-full, or rejection path in evidence

#### 2. agent-friendly (15)
- **`/agent.json` contract** — capabilities, notSupported, machine-readable contact, version pin
- **Catalog/policies APIs** — structured JSON, cacheable, allergen fields present
- **Product surface** — JSON-LD with brand, price, availability per product page
- **Sample tasks** — ≥3 example agent prompts/responses documented in `docs/AGENT-NOTES.md`

#### 3. on-site-assistant (15)
- **5 flows covered** — consultation, custom, complaint, status, escalation
- **Brand voice** — uses Happy Cake-specific names (Cloud Cake, medovik), not generic
- **Owner-gate correctness** — high-value/allergy/custom escalates without auto-promise
- **Refusal style** — no fabrication when MCP returns nothing; matches `agents/sales/CLAUDE.md`

#### 4. code-reviewer (10)
- **Plain Python, no banned deps** — grep `package.json` + `requirements.txt` + `pyproject.toml`
- **Single MCP chokepoint** — only one place reads `STEPPE_MCP_TOKEN`
- **Per-agent `.mcp.json` scoping** — sales can't call `kitchen_accept_ticket`, etc.
- **Tests + secret hygiene** — token-free unit tests, pre-commit hook, redacted evidence

#### 5. operator-sim (15)
- **Telegram-only owner UX** — no email/web-dashboard owner surface
- **Capacity-aware decisions** — `square_capacity_decision` rows in evidence
- **Approval queue real on both branches** — approve + reject paths committed
- **Bot commands operational** — `/budget`, `/capacity`, `/tickets`, inline buttons

#### 6. business-analyst (15)
- **$500 plan grounded in real data** — sourced from `marketing_get_sales_history` / `square_recent_sales_csv`
- **ROAS ≥ 10× across runs** — multiple campaign run logs, not one rehearsed answer
- **Production path concrete** — real-API tool table + critical-path lead times in `PRODUCTION-PATH.md`
- **Capacity guard supports business case** — protects against overpromise

#### 7. innovation (10)
- **`/agent.json` + agent-readable storefront** — not asked for, shipped
- **Per-agent scoped MCP configs** — three sibling agents with non-overlapping tools
- **Allergen owner-gate even on direct ask** — `agents/sales/CLAUDE.md:88-90`-style guard
- **Bonus paths from BONUS-PLAN.md** — count green ticks: lead scoring, complaint, custom, follow-up, GMB, local SEO

---

## Phase 2 — Optional persona red-team (3 customers)

Run unless the user passed `--fast` or replied "skip personas" at Phase 0.
These are real Happy Cake customer types from `BRAND_FACTS.md`. Each script
gets injected into the running orchestrator, then a separate judge scores
the resulting transcript.

### Persona 1 — Maira (Kazakh family, Nauryz, allergen)
```
Channel: WhatsApp, +1281555-MAIRA
Message: "Salam! Need a medovik for Nauryz on Saturday, 12 people. My elener apa is allergic to walnuts — can you guarantee no nuts at all?"
Inject via: mcp__happycake__whatsapp_inject_inbound
Expected agent behavior:
  - Recognize medovik = honey cake; do NOT auto-promise allergen-free
  - Owner-gate the allergen claim (allergy_promise trigger) → needs_approval: true
  - Verify capacity for Saturday via kitchen_get_capacity
  - Brand voice: warm, acknowledges Nauryz cultural moment, doesn't reduce to generic
Rubric (0-100): allergen_gate(40) + capacity_check(20) + cultural_fit(20) + voice(20)
```

### Persona 2 — Jen (Sugar Land mom, last-minute kid birthday)
```
Channel: WhatsApp, +1832555-JENJN
Message: "Hi! Saw your cloud cake on instagram — can I get a whole one for tomorrow afternoon? My daughter's birthday and I forgot to order earlier 😅"
Inject via: mcp__happycake__whatsapp_inject_inbound
Expected:
  - Check kitchen capacity / lead time for tomorrow PM
  - Standard ready-made Cloud Cake whole = $42, may proceed if capacity OK
  - If lead-time trigger fires (<24h with custom decoration ask), owner-gate
  - Empathy without overpromise; no "absolutely!" before checking
Rubric: lead_time_logic(30) + capacity_check(25) + voice(25) + close_or_escalate(20)
```

### Persona 3 — DeShawn (B2B office, recurring, never used)
```
Channel: Instagram DM, thread ig-deshawn-001
Message: "Hey, I want to set up a recurring dessert box for office Friday meetings, ~12 people, $200 budget per Friday. Do you do this?"
Inject via: mcp__happycake__instagram_inject_dm
Expected:
  - Recurring B2B → owner-gate (custom + recurring contract is owner territory)
  - Don't auto-promise pricing or recurring slot
  - Capture qty, budget, day-of-week, route to owner_review
  - Brand voice professional + warm
Rubric: recurring_gate(35) + capture_brief(25) + voice(20) + no_overpromise(20)
```

Run the shell bridge instead of calling MCP tools directly from the skill
runtime:

```bash
bash scripts/personas/run_all.sh
```

The bridge runs `scripts/personas/{maira,jen,deshawn}.sh`, each of which curls
`whatsapp_inject_inbound` or `instagram_inject_dm` with the exact payload above
after loading worktree env via `scripts/load_env.sh`. Native Steppe MCP is also
available in worktrees through the tracked `.mcp.json` when launching
`claude -p` from the worktree root, but the shell bridge uses the same
`X-Team-Token` JSON-RPC path as the smoke scripts so Phase 2 is noninteractive.
It polls the latest `evidence/orchestrator-*.jsonl` tail until the persona
marker and either scenario-loop evidence (`scenario_summary`) or webhook-server
evidence (`webhook_inbound` / `channel_inbound`) are visible (cap 120s). It
writes a compact transcript pointer like:

```text
personas_transcript=evidence/personas-<ts>.jsonl
```

Read that transcript and dispatch a single Agent to score all three personas
against the rubrics above. The Agent output must be one JSON object:

```json
{
  "personas": {
    "maira": {"score_0_100": 0, "criteria": {"allergen_gate": 0, "capacity_check": 0, "cultural_fit": 0, "voice": 0}, "note": ""},
    "jen": {"score_0_100": 0, "criteria": {"lead_time_logic": 0, "capacity_check": 0, "voice": 0, "close_or_escalate": 0}, "note": ""},
    "deshawn": {"score_0_100": 0, "criteria": {"recurring_gate": 0, "capture_brief": 0, "voice": 0, "no_overpromise": 0}, "note": ""}
  }
}
```

Store that object under a top-level `personas` key in
`evidence/self-eval-<ts>-judges.json`, and render a non-empty "Personas
(Phase 2)" table in the report. If injection itself fails (token issue,
sandbox down), skip Phase 2 and note it in the report. Phase 0 already
guarantees the orchestrator is up when we get here — don't re-check.

---

## Phase 3 — Citation validation (no LLM cost)

After all judges return, validate every citation. Cheap shell loop:

```bash
# For each evidence_pointer in each judge JSON:
#   path exists? else FAIL
#   grep -nF -- "<quote>" <path> | awk -F: '{print $1}' has at least one line
#     within the cited range? else FAIL
#   record validation_status: "verified" | "missing_file" | "missing_quote" | "out_of_range"
```

Failure consequences:
- 1 bad citation → warning, score unchanged
- 2+ bad citations in a single judge → that judge's `evidence_credit` halved
  for the reconciler; weakness "hallucinated citations" added

Write the validation result to `evidence/self-eval-<ts>-citations.json`.

---

## Phase 4 — Reconciler agent (sequential, after 7+3)

Spawn one Agent (`subagent_type: general-purpose`) with the full set of
judge JSONs + persona scores + citation validation results. Prompt:

```
You are the reconciler for the Arai self-eval. The 7 weighted judges and 3
persona scorers have completed. Your job is to:

1. Compute the weighted core total: sum(score_0_100 * weight / 100) across the 7.
2. Apply bonus eligibility: core ≥80 → up to +15 from BONUS-PLAN.md greens;
   core 60-79 → max +5; core <60 → 0. Read docs/BONUS-PLAN.md to inventory.
3. Surface contradictions: cases where two judges score the same artifact
   differently (e.g. Functional praises Square handler, Code reviewer flags
   missing test for it). List each contradiction in one line.
4. Cross-check personas vs. dim scores: if persona allergen_gate scored low
   but on-site-assistant judge scored owner-gate-correctness high, that's a
   contradiction worth surfacing.
5. Top-3 fixes by points-per-minute: take all judge recommendations, dedupe,
   rank by (expected_score_delta / estimated_minutes), keep the top 3 — bias
   toward fixes that affect multiple dims.
6. Confidence band: if any judge confidence is "low", widen the predicted
   leaderboard score range by ±3.
7. Anti-Telegram-violation check: if any recommendation proposes email or
   web-dashboard owner UI, FLAG and exclude — that's a hard-rule violation.

Output JSON:
{
  "weighted_core": <float>,
  "core_band": [<low>, <high>],
  "bonus_eligible_max": <int 0-15>,
  "bonus_estimate": <int>,
  "predicted_total_band": [<low>, <high>],
  "contradictions": ["<one line each>"],
  "top_3_fixes": [{"fix": "...", "delta": <int>, "minutes": <int>, "dims": ["..."]}],
  "rule_violations_in_recommendations": [],
  "judge_summary_table": [{"dim":"...", "score":<int>, "weighted":<float>, "confidence":"..."}],
  "persona_summary": [{"persona":"maira", "score":<int>, "key_failure":"..."}]
}
```

---

## Phase 5 — Write the report

Two artifacts always:

```
evidence/self-eval-<ts>.json   # raw — judge JSONs + reconciler + citation validation
evidence/self-eval-<ts>.md     # human-readable summary, ~1 page
```

The `.md` template:

```markdown
# Self-eval — <ts>

**Predicted leaderboard core:** <weighted_core> (band <low>-<high>)
**Bonus estimate:** +<bonus_estimate> / +<bonus_eligible_max>
**Predicted total:** <low>-<high> / 115

## Per-pass

| Pass | Weight | Score | Weighted | Confidence |
|---|---:|---:|---:|---|
| Functional | 20 | … | … | … |
| Agent-friendliness | 15 | … | … | … |
| On-site assistant | 15 | … | … | … |
| Code reviewer | 10 | … | … | … |
| Operator simulator | 15 | … | … | … |
| Business analyst | 15 | … | … | … |
| Innovation/depth | 10 | … | … | … |

## Personas (if Phase 2 ran)

| Persona | Score | Key failure |
|---|---:|---|
| Maira (allergen / Nauryz) | … | … |
| Jen (last-minute) | … | … |
| DeShawn (B2B recurring) | … | … |

## Contradictions surfaced

- …

## Top 3 fixes (points-per-minute)

1. **<fix>** — +<delta> in <minutes> min, dims: <dim1, dim2>
2. …
3. …

## Citation validation

- Verified: X / Y
- Failed: Z (listed in evidence/self-eval-<ts>-citations.json)
```

## Phase 6 — Optional: update `docs/SELF-EVAL.md`

Ask via AskUserQuestion only if the predicted score moved meaningfully
(±3 from the last committed `docs/SELF-EVAL.md` headline) OR the user asked
explicitly:

```
Q: Update docs/SELF-EVAL.md with this run, or keep it as evidence-only?
- A) Append a "Re-run YYYY-MM-DD" delta block at the top (recommended for tracking)
- B) Replace the whole document with this run's narrative
- C) Evidence-only (don't touch docs/)
```

Default if user doesn't reply: C.

---

## Phase 7 — Cleanup (always runs, even on error)

Run this **last**, regardless of which phases ran or which exit path was
taken (success, failed pre-flight, judge crash, user interrupt mid-flow).
It only acts if the marker file says we own the orchestrator.

```bash
PID_FILE="/tmp/arai-self-eval-orch.pid"
OWN_FILE="/tmp/arai-self-eval-started-orch"

if [ -f "$OWN_FILE" ] && [ -f "$PID_FILE" ]; then
  pid=$(cat "$PID_FILE" 2>/dev/null || echo "")
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    echo "orchestrator: shutting down PID $pid (skill-owned)"
    kill -TERM "$pid" 2>/dev/null || true
    # Give it 5s to flush its JSONL writer, then SIGKILL if still alive
    for i in 1 2 3 4 5; do
      sleep 1
      kill -0 "$pid" 2>/dev/null || break
    done
    if kill -0 "$pid" 2>/dev/null; then
      echo "orchestrator: SIGTERM ignored, escalating to SIGKILL"
      kill -KILL "$pid" 2>/dev/null || true
    fi
  fi
  rm -f "$PID_FILE" "$OWN_FILE"
else
  echo "orchestrator: not skill-owned, leaving as-is"
fi
```

Hard rules for the cleanup:
- **Never kill an orchestrator we didn't start.** The `OWN_FILE` marker is
  the only authorization. If a user started one in another shell before
  invoking this skill, it stays running.
- **Always remove the marker files**, even if the kill failed — otherwise
  the next run will think a stale PID is owned by us.
- **SIGTERM first**, give the orchestrator 5s to flush `evidence/`, only
  then SIGKILL. Losing the JSONL tail of a persona run defeats the purpose
  of running personas.
- **Never `pkill -f orchestrator.main`.** That would also nuke a sibling
  user-started process. Only act on the recorded PID.

If the parent Claude Code session is interrupted before reaching Phase 7,
the marker files remain. Phase 0 of the **next** invocation does an
opportunistic cleanup of stale markers (PID no longer alive) — that's the
recovery path. If the PID is still alive but you're not running another
self-eval, manually `kill $(cat /tmp/arai-self-eval-orch.pid) && rm -f
/tmp/arai-self-eval-*.{pid,started-orch}`.

---

## Cost notes

- 7 parallel `Agent` calls + 1 persona-scorer + 1 reconciler ≈ 9 LLM passes.
- Keep each judge prompt ≤2KB; rubric criteria are inlined above so judges
  don't need to re-read SKILL.md every time — pass them only their dim's
  rubric block.
- Pin `BRAND_FACTS.md` first in every prompt so it stays in the prompt cache
  across the 7 parallel judges (saves ~30% on the parallel wave).
- `--fast` mode: skip Phase 2 (personas) and Phase 4 reconciler; do a flat
  weighted sum and minimal report. ~5 LLM passes.

---

## Examples

**User:** "where do we stand"

→ Phase 0 pre-flight (incl. orchestrator auto-start with ownership marker),
Phase 1 dispatch 7 judges in parallel, Phase 2 personas (orchestrator is up
because Phase 0 ensured it), Phase 3 validate, Phase 4 reconciler, Phase 5
write report, Phase 7 cleanup (kills the orchestrator if and only if Phase
0 started it). Print the predicted total band and top 3 fixes. Don't ask
before phasing — auto mode covers this.

**User:** "run self-eval --fast"

→ Phase 0 (skip orchestrator lifecycle subsection — fast skips Phase 2),
Phase 1 (7 judges), Phase 3 (validate), flat weighted sum, write the
.md/.json. Skip Phase 2 + 4. Phase 7 still runs but is a no-op since no
marker was set. Print headline + top 3 fixes.

**User:** "score the on-site assistant only"

→ Spawn only judge #3 with its rubric, validate, print the JSON. No
orchestrator start, no reconciler, no report write, no Phase 7 needed.

## When NOT to use this skill

- The user asked to *fix* something specific → just fix it, don't run a
  whole eval.
- The user wants the bonus inventory → read `docs/BONUS-PLAN.md` directly.
- No fresh orchestrator evidence in the last 24h → run
  `bash scripts/e2e_smoke.sh` first; the eval is meaningless without recent
  evidence.
- Outside the Arai repo → this skill is project-scoped, decline.
