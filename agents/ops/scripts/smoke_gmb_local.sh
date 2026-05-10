#!/usr/bin/env bash
# Ops Agent — Google Business local-presence smoke.
#
# Exercises the non-review GMB simulator surface:
#   * metrics mode: gb_get_metrics(last_7_days), gb_get_metrics(last_30_days),
#     gb_list_simulated_actions
#   * post mode: gb_get_metrics(last_7_days), gb_list_simulated_actions,
#     gb_simulate_post, then owner-gate JSON with trigger=gmb_post_publish
#
# Usage:
#   bash agents/ops/scripts/smoke_gmb_local.sh
#   bash agents/ops/scripts/smoke_gmb_local.sh "Fresh cake \"Honey\" by the slice today until 5 PM."
# Requirements:
#   - .env.local, ARAI_ENV_FILE, or ~/.config/arai/env.local with STEPPE_MCP_TOKEN
#   - claude CLI v2.x, curl, jq on PATH

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
AGENT_DIR="$(cd "$HERE/.." && pwd)"
REPO_ROOT="$(cd "$AGENT_DIR/../.." && pwd)"

# shellcheck disable=SC1091
source "$REPO_ROOT/scripts/load_env.sh"
if ! arai_load_env "$REPO_ROOT"; then
  echo "error: env missing — create .env.local or ~/.config/arai/env.local with STEPPE_MCP_TOKEN" >&2
  exit 1
fi

if [ -z "${STEPPE_MCP_TOKEN:-}" ] || [ -z "${STEPPE_MCP_URL:-}" ]; then
  echo "error: STEPPE_MCP_TOKEN / STEPPE_MCP_URL not set after loading env" >&2
  exit 1
fi

LOG_DIR="$REPO_ROOT/evidence"
mkdir -p "$LOG_DIR"
TS_RUN=$(date -u +%Y%m%dT%H%M%SZ)
METRICS_LOG="$LOG_DIR/ops-gmb-local-metrics-$TS_RUN.log"
POST_LOG="$LOG_DIR/ops-gmb-local-post-$TS_RUN.log"
SAMPLE_OUT="$LOG_DIR/ops-sample.jsonl"

DEFAULT_TRIGGER_DETAIL="Fresh cake \"Honey\" by the slice today until 5 PM. Whole cake \"Pistachio Roll\" is available for pickup after noon. Order at happycake.us/order."
TRIGGER_DETAIL="${1:-$DEFAULT_TRIGGER_DETAIL}"

mcp_call() {
  local tool="$1" args="$2"
  curl -sS \
    -H "X-Team-Token: $STEPPE_MCP_TOKEN" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"$tool\",\"arguments\":$args}}" \
    "$STEPPE_MCP_URL"
}

run_claude_stream() {
  local prompt="$1" log="$2"
  cd "$AGENT_DIR"
  set +e
  claude -p "$prompt" \
    --permission-mode bypassPermissions \
    --output-format stream-json \
    --verbose \
    > "$log"
  local rc=$?
  set -e
  return $rc
}

tools_used() {
  local log="$1"
  jq -c -r '
    select(.type=="assistant") | .message.content[]? |
    select(.type=="tool_use") | .name
  ' "$log" | sort -u | jq -R . | jq -sc .
}

result_text() {
  local log="$1"
  jq -c 'select(.type=="result")' "$log" | tail -n 1 | jq -r '.result // ""'
}

result_turns() {
  local log="$1"
  jq -c 'select(.type=="result")' "$log" | tail -n 1 | jq -r '.num_turns // 0'
}

has_tool() {
  local log="$1" tool="$2"
  jq -e --arg tool "$tool" '
    select(.type=="assistant") | .message.content[]? |
    select(.type=="tool_use" and .name == $tool)
  ' "$log" >/dev/null
}

owner_gate_json() {
  python3 -c '
import json, sys
text = sys.stdin.read()
depth = 0
start = -1
for i, ch in enumerate(text):
    if ch == "{":
        if depth == 0:
            start = i
        depth += 1
    elif ch == "}":
        depth -= 1
        if depth == 0 and start >= 0:
            try:
                print(json.dumps(json.loads(text[start:i+1])))
                sys.exit(0)
            except json.JSONDecodeError:
                start = -1
sys.exit(0)
'
}

AUDIT_BEFORE=$(mcp_call evaluator_get_evidence_summary '{}' \
  | jq -r '.result.content[0].text' | jq -r '.counts.auditCalls // 0')
echo "[$(date -u +%FT%TZ)] auditCalls before: $AUDIT_BEFORE"

TEMPLATE="$(cat "$AGENT_DIR/PROMPTS/gmb_local_presence.md")"

echo
echo "===== stage 1 — metrics ====="
METRICS_PROMPT="${TEMPLATE//'{{mode}}'/metrics}"
METRICS_PROMPT="${METRICS_PROMPT//'{{trigger}}'/local_presence_smoke}"
METRICS_PROMPT="${METRICS_PROMPT//'{{trigger_detail}}'/$TRIGGER_DETAIL}"
run_claude_stream "$METRICS_PROMPT" "$METRICS_LOG" || \
  echo "[$(date -u +%FT%TZ)] claude -p (metrics) exited non-zero" >&2

METRICS_TOOLS=$(tools_used "$METRICS_LOG")
METRICS_RESULT=$(result_text "$METRICS_LOG")
METRICS_PASS="false"
METRICS_DETAIL="missing one or more required metrics tools"
if has_tool "$METRICS_LOG" "mcp__happycake__gb_get_metrics" \
   && has_tool "$METRICS_LOG" "mcp__happycake__gb_list_simulated_actions"; then
  METRICS_PASS="true"
  METRICS_DETAIL="gb_get_metrics and gb_list_simulated_actions called"
fi
echo "[$(date -u +%FT%TZ)] metrics tools_used=$METRICS_TOOLS"
echo "[$(date -u +%FT%TZ)] stage 1: $( [ "$METRICS_PASS" = "true" ] && echo PASS || echo FAIL ) — $METRICS_DETAIL"

echo
echo "===== stage 2 — proposed local post ====="
POST_PROMPT="${TEMPLATE//'{{mode}}'/post}"
POST_PROMPT="${POST_PROMPT//'{{trigger}}'/local_post_smoke}"
POST_PROMPT="${POST_PROMPT//'{{trigger_detail}}'/$TRIGGER_DETAIL}"
run_claude_stream "$POST_PROMPT" "$POST_LOG" || \
  echo "[$(date -u +%FT%TZ)] claude -p (post) exited non-zero" >&2

POST_TOOLS=$(tools_used "$POST_LOG")
POST_RESULT=$(result_text "$POST_LOG")
POST_GATE=$(echo "$POST_RESULT" | owner_gate_json)
POST_GATE_TRIGGER=$(echo "$POST_GATE" | jq -r '.trigger // empty')
POST_GATE_CHANNEL=$(echo "$POST_GATE" | jq -r '.channel // empty')
POST_NEEDS_APPROVAL=$(echo "$POST_GATE" | jq -r '.needs_approval // false')
POST_DRAFT=$(echo "$POST_GATE" | jq -r '.draft // empty')
POST_NUM_TURNS=$(result_turns "$POST_LOG")

POST_PASS="false"
POST_DETAIL="post proposal did not meet owner-gate criteria"
if has_tool "$POST_LOG" "mcp__happycake__gb_simulate_post" \
   && [ "$POST_NEEDS_APPROVAL" = "true" ] \
   && [ "$POST_GATE_TRIGGER" = "gmb_post_publish" ] \
   && [ "$POST_GATE_CHANNEL" = "gmb" ] \
   && [ -n "$POST_DRAFT" ]; then
  POST_PASS="true"
  POST_DETAIL="gb_simulate_post called; owner-gate JSON returned with trigger=gmb_post_publish"
fi
echo "[$(date -u +%FT%TZ)] post tools_used=$POST_TOOLS"
echo "[$(date -u +%FT%TZ)] stage 2: $( [ "$POST_PASS" = "true" ] && echo PASS || echo FAIL ) — $POST_DETAIL"

AUDIT_AFTER=$(mcp_call evaluator_get_evidence_summary '{}' \
  | jq -r '.result.content[0].text' | jq -r '.counts.auditCalls // 0')
AUDIT_DELTA=$(( AUDIT_AFTER - AUDIT_BEFORE ))
echo "[$(date -u +%FT%TZ)] auditCalls delta: $AUDIT_BEFORE -> $AUDIT_AFTER (+$AUDIT_DELTA)"

RESULT="FAIL"
DETAIL="metrics: $METRICS_DETAIL; post: $POST_DETAIL"
if [ "$METRICS_PASS" = "true" ] && [ "$POST_PASS" = "true" ]; then
  RESULT="PASS"
fi

TS=$(date -u +%FT%TZ)
POST_PREVIEW=$(echo "$POST_DRAFT" | tr '\n' ' ' | head -c 280 \
  | sed -E 's/[A-Za-z0-9]{32,}/<REDACTED>/g')
METRICS_PREVIEW=$(echo "$METRICS_RESULT" | tr '\n' ' ' | head -c 280 \
  | sed -E 's/[A-Za-z0-9]{32,}/<REDACTED>/g')

SAMPLE_ROW=$(jq -nc \
  --arg ts "$TS" \
  --arg result "$RESULT" \
  --arg detail "$DETAIL" \
  --argjson metrics_tools "$METRICS_TOOLS" \
  --argjson post_tools "$POST_TOOLS" \
  --arg post_preview "$POST_PREVIEW" \
  --arg metrics_preview "$METRICS_PREVIEW" \
  --arg post_turns "$POST_NUM_TURNS" \
  --arg audit_before "$AUDIT_BEFORE" \
  --arg audit_after "$AUDIT_AFTER" \
  '{
    ts: $ts,
    test: "ops_gmb_local_presence_smoke",
    result: $result,
    detail: $detail,
    metrics_tools_used: $metrics_tools,
    post_tools_used: $post_tools,
    metrics_preview: $metrics_preview,
    post_preview: $post_preview,
    post_num_turns: ($post_turns | tonumber),
    audit_calls_before: ($audit_before | tonumber),
    audit_calls_after: ($audit_after | tonumber)
  }')
echo "$SAMPLE_ROW" >> "$SAMPLE_OUT"

echo
echo "===== ops gmb local smoke result ====="
echo "$RESULT  $DETAIL"
echo "metrics log: $METRICS_LOG"
echo "post log:    $POST_LOG"
echo "sample:      $SAMPLE_OUT"
echo "row:"
echo "  $SAMPLE_ROW"

if [ "$RESULT" = "PASS" ]; then
  exit 0
else
  exit 1
fi
