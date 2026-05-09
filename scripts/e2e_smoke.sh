#!/usr/bin/env bash
# e2e_smoke.sh — bounded end-to-end smoke for the Arai system.
#
# Touches all four scoring loops in one bash command, ≤ 5 min wall-clock:
#
#   1. Preflight: orchestrator --dry-run
#   2. Verify .env.local has STEPPE_MCP_TOKEN
#   3. Sanity-check MCP wiring via tools/list (>= 50 tools)
#   4. Start orchestrator on a bounded scenario (background)
#   5. Inject WA + IG + GMB events to exercise the channel handlers
#   6. Wait for orchestrator with a hard wall-clock kill
#   7. Call evaluator_get_evidence_summary + four evaluator_score_*
#      tools + evaluator_generate_team_report; print PASS/FAIL
#
# On PASS, also writes the last 50 lines of the orchestrator's JSONL run
# to evidence/e2e-sample.jsonl with belt-and-braces token redaction.
#
# Usage:
#   bash scripts/e2e_smoke.sh
#
# Tunables (env):
#   SMOKE_SCENARIO       (default launch-day-revenue-engine)
#   SMOKE_MAX_EVENTS     (default 12 — covers 6 seeded + 4 injects + slack)
#   SMOKE_ORCH_TIMEOUT   (default 420 — hard wall-clock kill, seconds)
#   PYTHON               (default orchestrator/.venv/bin/python)
#
# Exit codes: 0 PASS, 1 setup failure, 2 redaction tripwire, 3 score FAIL.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

SCENARIO="${SMOKE_SCENARIO:-launch-day-revenue-engine}"
MAX_EVENTS="${SMOKE_MAX_EVENTS:-12}"
ORCH_TIMEOUT="${SMOKE_ORCH_TIMEOUT:-420}"
PYTHON="${PYTHON:-orchestrator/.venv/bin/python}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"

red()    { printf '\033[31m%s\033[0m\n' "$*"; }
green()  { printf '\033[32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[33m%s\033[0m\n' "$*"; }
plain()  { printf '%s\n' "$*"; }

START_EPOCH=$(date +%s)

plain "=== Arai E2E Smoke @ ${TS} ==="
plain "scenario=${SCENARIO}  max_events=${MAX_EVENTS}  budget=${ORCH_TIMEOUT}s"
plain ""

# ---------- 1. Preflight ---------------------------------------------------
yellow "[1/7] Orchestrator dry-run"
if [[ ! -x "$PYTHON" ]]; then
  red "  python venv not found at $PYTHON — run: cd orchestrator && uv venv --python 3.12 .venv && uv pip install -r requirements.txt"
  exit 1
fi
if PYTHONPATH=orchestrator "$PYTHON" -m orchestrator.main --dry-run \
     > /tmp/arai-smoke-dryrun.log 2>&1; then
  green "  dry-run OK"
else
  red "  dry-run FAILED — see /tmp/arai-smoke-dryrun.log"
  tail -40 /tmp/arai-smoke-dryrun.log >&2
  exit 1
fi

# ---------- 2. Token -------------------------------------------------------
yellow "[2/7] Verify STEPPE_MCP_TOKEN in .env.local"
if [[ ! -f .env.local ]]; then
  red "  .env.local missing — copy .env.example and fill STEPPE_MCP_TOKEN"
  exit 1
fi
set -a
# shellcheck disable=SC1091
source .env.local
set +a
if [[ -z "${STEPPE_MCP_TOKEN:-}" ]]; then
  red "  STEPPE_MCP_TOKEN not set after sourcing .env.local"
  exit 1
fi
: "${STEPPE_MCP_URL:=https://www.steppebusinessclub.com/api/mcp}"
green "  STEPPE_MCP_TOKEN present, MCP URL=${STEPPE_MCP_URL}"

# ---------- 3. Tool list sanity --------------------------------------------
yellow "[3/7] MCP tools/list — assert >= 50 tools"
tool_count=$(PYTHONPATH=orchestrator "$PYTHON" - <<'PY' 2>/tmp/arai-smoke-tools.err
from orchestrator.mcp_client import MCPClient
with MCPClient.from_env() as c:
    print(len(c.list_tools()))
PY
)
if [[ -z "$tool_count" ]]; then
  red "  tools/list call failed — see /tmp/arai-smoke-tools.err"
  cat /tmp/arai-smoke-tools.err >&2 || true
  exit 1
fi
if (( tool_count >= 50 )); then
  green "  tool count = ${tool_count} (>= 50)"
else
  red "  tool count = ${tool_count} (< 50) — MCP wiring not healthy"
  exit 1
fi

# ---------- 4. Start orchestrator (background) ----------------------------
yellow "[4/7] Start orchestrator (bg) scenario=${SCENARIO} max-events=${MAX_EVENTS}"
ORCH_LOG="/tmp/arai-smoke-orchestrator-${TS}.log"
PYTHONPATH=orchestrator "$PYTHON" -m orchestrator.main \
    --scenario "$SCENARIO" \
    --max-events "$MAX_EVENTS" \
    --log-level INFO \
    > "$ORCH_LOG" 2>&1 &
ORCH_PID=$!
plain "  pid=${ORCH_PID}  log=${ORCH_LOG}"

cleanup() {
  if kill -0 "$ORCH_PID" 2>/dev/null; then
    kill "$ORCH_PID" 2>/dev/null || true
    wait "$ORCH_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

# Wait until orchestrator has actually called world_start_scenario, so our
# injects land in this scenario (start resets the team timeline).
for _ in $(seq 1 30); do
  if grep -qE 'Scenario .* started|starting scenario|world_start_scenario' "$ORCH_LOG" 2>/dev/null; then
    break
  fi
  sleep 0.5
done

# ---------- 5. Inject sanity events ---------------------------------------
yellow "[5/7] Inject WA + IG + GMB sanity events"

call_tool() {
  # $1 tool name, $2 args (JSON object as string). Default args = empty object.
  # NOTE: don't write "${2:-{}}" — bash's brace matching mangles the default.
  local tool="$1"
  local args="${2:-}"
  [[ -z "$args" ]] && args='{}'
  local body
  body=$(jq -n --arg name "$tool" --argjson args "$args" \
    '{jsonrpc:"2.0", id:(now|floor), method:"tools/call", params:{name:$name, arguments:$args}}')
  curl -sS \
    -H "X-Team-Token: ${STEPPE_MCP_TOKEN}" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -d "$body" \
    "$STEPPE_MCP_URL"
}

extract_text() {
  jq -r '.result.content[0].text // empty'
}

inj_wa_order=$(call_tool whatsapp_inject_inbound \
  '{"from":"+128****0100","message":"Hi! I would like to order one medium honey cake (Medovik), pickup tomorrow at 4pm. My name is Sam."}' | extract_text)
plain "  WA  inject (order)   -> ${inj_wa_order:-(empty)}" | head -c 200; plain ""

inj_wa_q=$(call_tool whatsapp_inject_inbound \
  '{"from":"+128****0101","message":"What time do you close today?"}' | extract_text)
plain "  WA  inject (inquiry) -> ${inj_wa_q:-(empty)}" | head -c 200; plain ""

inj_ig=$(call_tool instagram_inject_dm \
  '{"threadId":"smoke-thread-001","from":"smoketest_user","message":"Hi! Looking for a birthday cake for next Saturday — what do you recommend?"}' | extract_text)
plain "  IG  inject (DM)      -> ${inj_ig:-(empty)}" | head -c 200; plain ""

inj_gmb=$(call_tool world_inject_event \
  "$(jq -nc --arg ts "$TS" '{channel:"gmb", type:"review_received", payload:{reviewId:("rev_smoke_"+$ts), rating:5, author:"Smoke Test", text:"Tried the honey cake — really tender. Will be back."}}')" | extract_text)
plain "  GMB inject (review)  -> ${inj_gmb:-(empty)}" | head -c 200; plain ""

green "  injected 4 events (1 order + 1 inquiry + 1 IG DM + 1 GMB review)"

# ---------- 6. Wait for orchestrator with hard wall-clock kill ------------
yellow "[6/7] Wait for orchestrator (hard timeout ${ORCH_TIMEOUT}s)"
elapsed=0
while kill -0 "$ORCH_PID" 2>/dev/null; do
  if (( elapsed >= ORCH_TIMEOUT )); then
    yellow "  hit ${ORCH_TIMEOUT}s budget — sending SIGTERM"
    kill "$ORCH_PID" 2>/dev/null || true
    sleep 2
    kill -9 "$ORCH_PID" 2>/dev/null || true
    break
  fi
  sleep 2
  elapsed=$((elapsed + 2))
done
wait "$ORCH_PID" 2>/dev/null || true
trap - EXIT
green "  orchestrator finished after ~${elapsed}s"

# ---------- 7. Evaluator scoring ------------------------------------------
yellow "[7/7] Call evaluator_get_evidence_summary + four evaluator_score_* + team_report"

mkdir -p evidence
OUT="evidence/e2e-smoke-${TS}.json"

call_unwrap() {
  # Wraps call_tool, returns either the parsed JSON payload or the literal
  # string "null" so jq downstream stays valid.
  local tool="$1"
  local args="${2:-}"
  [[ -z "$args" ]] && args='{}'
  local raw
  raw=$(call_tool "$tool" "$args")
  local text
  text=$(printf '%s' "$raw" | jq -r '.result.content[0].text // empty')
  if [[ -z "$text" ]]; then
    if printf '%s' "$raw" | jq -e '.error' >/dev/null 2>&1; then
      printf '%s' "$raw" | jq '{error:.error}'
    else
      printf 'null'
    fi
  else
    printf '%s' "$text" | jq '.'
  fi
}

ev_summary=$(call_unwrap evaluator_get_evidence_summary)
sc_marketing=$(call_unwrap evaluator_score_marketing_loop)
sc_pos=$(call_unwrap evaluator_score_pos_kitchen_flow)
sc_channel=$(call_unwrap evaluator_score_channel_response)
sc_world=$(call_unwrap evaluator_score_world_scenario)
team_report=$(call_unwrap evaluator_generate_team_report \
  '{"repoUrl":"https://github.com/Jandos22/Arai","notes":"Arai e2e smoke — Jan Solo"}')

jq -n \
  --argjson evidence "$ev_summary" \
  --argjson marketing "$sc_marketing" \
  --argjson pos_kitchen "$sc_pos" \
  --argjson channels "$sc_channel" \
  --argjson world "$sc_world" \
  --argjson team_report "$team_report" \
  --arg ts "$TS" \
  '{ts:$ts,
    evidence:$evidence,
    scores:{marketing:$marketing, pos_kitchen:$pos_kitchen, channels:$channels, world:$world},
    team_report:$team_report}' \
  > "$OUT"

plain ""
plain "=== EVALUATOR PREVIEW @ ${TS} ==="
jq -r '
  "marketing       : " + ((.scores.marketing.score      // .scores.marketing      // "n/a") | tostring),
  "pos_kitchen     : " + ((.scores.pos_kitchen.score    // .scores.pos_kitchen    // "n/a") | tostring),
  "channels        : " + ((.scores.channels.score       // .scores.channels       // "n/a") | tostring),
  "world           : " + ((.scores.world.score          // .scores.world          // "n/a") | tostring)
' "$OUT"
plain "(full payload at ${OUT})"

# Pass criteria: each of the four score calls returned a non-error response.
ok=1
for label in marketing pos_kitchen channels world; do
  if jq -e --arg k "$label" '
        .scores[$k] == null
        or (.scores[$k] | type) != "object"
        or (.scores[$k].error // false)
      ' "$OUT" >/dev/null; then
    red "  score loop '$label' returned error or empty"
    ok=0
  fi
done

# Capture redacted evidence sample on PASS.
if (( ok )); then
  yellow "Capturing redacted evidence sample (last 50 lines)"
  latest=$(ls -t evidence/orchestrator-run-*.jsonl 2>/dev/null | head -1 || true)
  if [[ -n "$latest" && -s "$latest" ]]; then
    tail -n 50 "$latest" \
      | sed -E 's/sbc_team_[A-Za-z0-9_-]+/[REDACTED]/g' \
      | sed -E 's/(Bearer[[:space:]]+)[A-Za-z0-9._-]{20,}/\1[REDACTED]/g' \
      | sed -E 's/(X-Team-Token["'\''[:space:]:=]+)[A-Za-z0-9_-]{16,}/\1[REDACTED]/g' \
      > evidence/e2e-sample.jsonl
    if grep -iE 'sbc_team|bearer ' evidence/e2e-sample.jsonl >/dev/null; then
      red "  WARNING: token-like content remains in evidence/e2e-sample.jsonl"
      exit 2
    fi
    green "  wrote evidence/e2e-sample.jsonl ($(wc -l < evidence/e2e-sample.jsonl | tr -d ' ') lines)"
  else
    yellow "  no orchestrator-run-*.jsonl produced — skipping sample"
  fi
fi

ELAPSED_TOTAL=$(( $(date +%s) - START_EPOCH ))
plain ""
if (( ok )); then
  green "==== PASS  total=${ELAPSED_TOTAL}s ===="
  exit 0
else
  red   "==== FAIL  total=${ELAPSED_TOTAL}s ===="
  exit 3
fi
