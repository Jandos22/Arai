#!/usr/bin/env bash
# Sales Agent — end-to-end smoke against the live sandbox.
#
# 1. Source repo .env.local for STEPPE_MCP_URL / STEPPE_MCP_TOKEN.
# 2. Snapshot the sandbox audit-call counter via evaluator_get_evidence_summary.
# 3. Inject a fake inbound WhatsApp message via whatsapp_inject_inbound.
# 4. Run `claude -p` from agents/sales/ with the orchestrator-style prompt
#    in stream-json mode so we can capture every tool_use the model makes.
# 5. Verify the agent either (a) called mcp__happycake__whatsapp_send, or
#    (b) returned the owner-gate JSON. Anything else is a FAIL.
# 6. Append one summary row to evidence/sales-sample.jsonl, print PASS/FAIL.
#
# Sandbox quirk we work around: whatsapp_send returns "[simulated] Message
# recorded ..." and increments the auditCalls counter, but
# whatsapp_list_threads.outbound stays empty and
# evaluator_get_evidence_summary.whatsappOutbound stays 0. The proof the
# call landed is the tool_use event in the stream-json output, plus the
# auditCalls delta from before/after.
#
# Usage:
#   bash agents/sales/scripts/smoke.sh
#   bash agents/sales/scripts/smoke.sh "I want to order 2 whole honey cakes for tomorrow at 5pm"
# Requirements:
#   - .env.local at repo root with STEPPE_MCP_URL + STEPPE_MCP_TOKEN
#   - claude CLI v2.x, curl, jq on PATH

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
AGENT_DIR="$(cd "$HERE/.." && pwd)"
REPO_ROOT="$(cd "$AGENT_DIR/../.." && pwd)"

if [ ! -f "$REPO_ROOT/.env.local" ]; then
  echo "error: $REPO_ROOT/.env.local missing" >&2
  exit 1
fi
# shellcheck disable=SC1091
set -a; source "$REPO_ROOT/.env.local"; set +a

if [ -z "${STEPPE_MCP_TOKEN:-}" ] || [ -z "${STEPPE_MCP_URL:-}" ]; then
  echo "error: STEPPE_MCP_TOKEN / STEPPE_MCP_URL not set after sourcing .env.local" >&2
  exit 1
fi

SMOKE_FROM="+12815550199"
DEFAULT_MSG="Do you have honey cake today?"
SMOKE_MSG="${1:-$DEFAULT_MSG}"

LOG_DIR="$REPO_ROOT/evidence"
mkdir -p "$LOG_DIR"
RUN_LOG="$LOG_DIR/sales-smoke-$(date -u +%Y%m%dT%H%M%SZ).log"
SAMPLE_OUT="$LOG_DIR/sales-sample.jsonl"

echo "[$(date -u +%FT%TZ)] sales smoke → $RUN_LOG"
echo "[$(date -u +%FT%TZ)]   from=$SMOKE_FROM"
echo "[$(date -u +%FT%TZ)]   message=$SMOKE_MSG"

mcp_call() {
  local tool="$1" args="$2"
  curl -sS \
    -H "X-Team-Token: $STEPPE_MCP_TOKEN" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"$tool\",\"arguments\":$args}}" \
    "$STEPPE_MCP_URL"
}

# 1. Pre-run audit-call snapshot.
AUDIT_BEFORE=$(mcp_call evaluator_get_evidence_summary '{}' \
  | jq -r '.result.content[0].text' | jq -r '.counts.auditCalls // 0')
echo "[$(date -u +%FT%TZ)] auditCalls before: $AUDIT_BEFORE"

# 2. Inject inbound.
INJECT_PAYLOAD=$(jq -nc --arg from "$SMOKE_FROM" --arg msg "$SMOKE_MSG" \
  '{from:$from, message:$msg}')
echo "[$(date -u +%FT%TZ)] injecting inbound"
mcp_call whatsapp_inject_inbound "$INJECT_PAYLOAD" >/dev/null

# 3. Run the agent with stream-json so we can see every tool_use.
PROMPT_TEMPLATE="$(cat "$AGENT_DIR/PROMPTS/whatsapp_inbound.md")"
PROMPT="${PROMPT_TEMPLATE//'{{from}}'/$SMOKE_FROM}"
PROMPT="${PROMPT//'{{message}}'/$SMOKE_MSG}"

cd "$AGENT_DIR"
echo "[$(date -u +%FT%TZ)] launching claude -p (--output-format stream-json --verbose)"
set +e
claude -p "$PROMPT" \
  --permission-mode bypassPermissions \
  --output-format stream-json \
  --verbose \
  > "$RUN_LOG"
CLAUDE_EXIT=$?
set -e

# 4. Parse the stream for tool_use names + the final result text.
TOOLS_USED=$(jq -c -r '
  select(.type=="assistant") | .message.content[]? |
  select(.type=="tool_use") | .name
' "$RUN_LOG" | sort -u | jq -R . | jq -sc .)

WHATSAPP_SEND_CALLED=$(jq -r '
  select(.type=="assistant") | .message.content[]? |
  select(.type=="tool_use" and .name=="mcp__happycake__whatsapp_send") |
  .input.to
' "$RUN_LOG" | head -n 1)

# Pull the final result event (single line at end of stream).
RESULT_EVENT=$(jq -c 'select(.type=="result")' "$RUN_LOG" | tail -n 1)
RESULT_TEXT=$(echo "$RESULT_EVENT" | jq -r '.result // ""')
NUM_TURNS=$(echo "$RESULT_EVENT" | jq -r '.num_turns // 0')
TOTAL_COST=$(echo "$RESULT_EVENT" | jq -r '.total_cost_usd // 0')
IS_ERROR=$(echo "$RESULT_EVENT" | jq -r '.is_error // false')
PERM_DENIALS=$(echo "$RESULT_EVENT" | jq -c '.permission_denials // []')

# 5. Detect owner-gate path (final result is a JSON object with needs_approval).
NEEDS_APPROVAL="false"
if echo "$RESULT_TEXT" | grep -q '"needs_approval"[[:space:]]*:[[:space:]]*true'; then
  NEEDS_APPROVAL="true"
fi

# 6. Post-run audit-call delta.
AUDIT_AFTER=$(mcp_call evaluator_get_evidence_summary '{}' \
  | jq -r '.result.content[0].text' | jq -r '.counts.auditCalls // 0')
AUDIT_DELTA=$(( AUDIT_AFTER - AUDIT_BEFORE ))

echo
echo "----- agent reply -----"
echo "$RESULT_TEXT"
echo "-----------------------"
echo "[$(date -u +%FT%TZ)] tools_used=$TOOLS_USED"
echo "[$(date -u +%FT%TZ)] whatsapp_send.to=${WHATSAPP_SEND_CALLED:-<none>}"
echo "[$(date -u +%FT%TZ)] num_turns=$NUM_TURNS  cost=$TOTAL_COST  is_error=$IS_ERROR  perm_denials=$PERM_DENIALS"
echo "[$(date -u +%FT%TZ)] auditCalls delta: $AUDIT_BEFORE → $AUDIT_AFTER  (+$AUDIT_DELTA)"

if [ "$CLAUDE_EXIT" -ne 0 ]; then
  echo "[$(date -u +%FT%TZ)] claude -p exited $CLAUDE_EXIT" >&2
fi

# 7. Decide PASS / FAIL.
RESULT="FAIL"
DETAIL=""
if [ -n "$WHATSAPP_SEND_CALLED" ] && [ "$WHATSAPP_SEND_CALLED" = "$SMOKE_FROM" ]; then
  RESULT="PASS"
  DETAIL="whatsapp_send called with to=$SMOKE_FROM"
elif [ -n "$WHATSAPP_SEND_CALLED" ]; then
  RESULT="FAIL"
  DETAIL="whatsapp_send called with WRONG to=$WHATSAPP_SEND_CALLED (expected $SMOKE_FROM)"
elif [ "$NEEDS_APPROVAL" = "true" ]; then
  RESULT="PASS"
  DETAIL="owner-gate JSON returned (needs_approval=true) — by design no whatsapp_send"
else
  RESULT="FAIL"
  DETAIL="agent did not call whatsapp_send and did not return needs_approval JSON"
fi

# 8. Append one structured row to evidence/sales-sample.jsonl.
TS=$(date -u +%FT%TZ)
RESPONSE_PREVIEW=$(echo "$RESULT_TEXT" | tr '\n' ' ' | head -c 280 \
  | sed -E 's/[A-Za-z0-9]{32,}/<REDACTED>/g')
SAMPLE_ROW=$(jq -nc \
  --arg ts "$TS" \
  --arg from "$SMOKE_FROM" \
  --arg msg "$SMOKE_MSG" \
  --arg result "$RESULT" \
  --arg detail "$DETAIL" \
  --arg preview "$RESPONSE_PREVIEW" \
  --arg num_turns "$NUM_TURNS" \
  --arg cost "$TOTAL_COST" \
  --arg is_error "$IS_ERROR" \
  --argjson tools "$TOOLS_USED" \
  --argjson approval "$( [ "$NEEDS_APPROVAL" = "true" ] && echo true || echo false )" \
  --arg audit_before "$AUDIT_BEFORE" \
  --arg audit_after "$AUDIT_AFTER" \
  '{
    ts: $ts,
    test: "sales_whatsapp_smoke",
    inbound: { from: $from, message: $msg },
    result: $result,
    detail: $detail,
    needs_approval: $approval,
    tools_used: $tools,
    response_preview: $preview,
    num_turns: ($num_turns | tonumber),
    total_cost_usd: ($cost | tonumber),
    is_error: ($is_error == "true"),
    audit_calls_before: ($audit_before | tonumber),
    audit_calls_after: ($audit_after | tonumber)
  }')
echo "$SAMPLE_ROW" >> "$SAMPLE_OUT"

echo
echo "===== sales smoke result ====="
echo "$RESULT  $DETAIL"
echo "log:    $RUN_LOG"
echo "sample: $SAMPLE_OUT"
echo "row:"
echo "  $SAMPLE_ROW"

if [ "$RESULT" = "PASS" ]; then
  exit 0
else
  exit 1
fi
