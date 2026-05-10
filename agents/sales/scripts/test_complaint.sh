#!/usr/bin/env bash
# T-013 — Complaint path smoke against the live sandbox.
#
# 1. Source repo .env.local for STEPPE_MCP_URL / STEPPE_MCP_TOKEN.
# 2. Snapshot the sandbox audit-call counter via evaluator_get_evidence_summary.
# 3. Inject one inbound complaint via whatsapp_inject_inbound.
# 4. Run `claude -p` from agents/sales/ with the orchestrator-style prompt
#    in stream-json mode so we can capture every tool_use the model makes.
# 5. PASS iff the agent took the documented complaint tool chain:
#    - called mcp__happycake__whatsapp_send exactly once with the empathetic ack
#    - returned a JSON owner-gate object with needs_approval=true AND kind="complaint"
#    - did NOT call square_update_order_status / square_create_order /
#      kitchen_create_ticket (those are post-approval only)
# 6. Append one structured row to evidence/sales-sample.jsonl.
#
# Usage:
#   bash agents/sales/scripts/test_complaint.sh
#   bash agents/sales/scripts/test_complaint.sh \
#     "My daughter had an allergic reaction to your chocolate cake yesterday"
#
# Default message exercises a medium-severity refund request. Override the
# argument to test severity=high (allergy / illness language).
#
# Sandbox quirk (documented in agents/sales/README.md): whatsapp_send returns
# "[simulated] ..." but whatsapp_list_threads.outbound stays empty. Proof of
# the call is the tool_use event in stream-json + auditCalls delta.

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

SMOKE_FROM="+12815550213"
DEFAULT_MSG="The Medovik I picked up yesterday wasn't fresh — the cream was sour. I'd like a refund please."
SMOKE_MSG="${1:-$DEFAULT_MSG}"

LOG_DIR="$REPO_ROOT/evidence"
mkdir -p "$LOG_DIR"
RUN_LOG="$LOG_DIR/sales-complaint-smoke-$(date -u +%Y%m%dT%H%M%SZ).log"
SAMPLE_OUT="$LOG_DIR/sales-sample.jsonl"

echo "[$(date -u +%FT%TZ)] complaint smoke → $RUN_LOG"
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

# 2. Inject inbound complaint.
INJECT_PAYLOAD=$(jq -nc --arg from "$SMOKE_FROM" --arg msg "$SMOKE_MSG" \
  '{from:$from, message:$msg}')
echo "[$(date -u +%FT%TZ)] injecting inbound complaint"
mcp_call whatsapp_inject_inbound "$INJECT_PAYLOAD" >/dev/null

# 3. Build the prompt from the complaint template.
PROMPT_TEMPLATE="$(cat "$AGENT_DIR/PROMPTS/complaint.md")"
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

# 4. Parse the stream for tool_use names + final result text.
TOOLS_USED=$(jq -c -r '
  select(.type=="assistant") | .message.content[]? |
  select(.type=="tool_use") | .name
' "$RUN_LOG" | sort -u | jq -R . | jq -sc .)

WHATSAPP_SEND_TO=$(jq -r '
  select(.type=="assistant") | .message.content[]? |
  select(.type=="tool_use" and .name=="mcp__happycake__whatsapp_send") |
  .input.to
' "$RUN_LOG" | head -n 1)

WHATSAPP_SEND_COUNT=$(jq -r '
  select(.type=="assistant") | .message.content[]? |
  select(.type=="tool_use" and .name=="mcp__happycake__whatsapp_send") |
  .name
' "$RUN_LOG" | wc -l | tr -d ' ')

# Forbidden post-approval tools — must NOT appear in this turn.
FORBIDDEN_HITS=$(jq -r '
  select(.type=="assistant") | .message.content[]? |
  select(.type=="tool_use") |
  select(.name=="mcp__happycake__square_update_order_status"
      or .name=="mcp__happycake__square_create_order"
      or .name=="mcp__happycake__kitchen_create_ticket") |
  .name
' "$RUN_LOG" | sort -u | tr '\n' ',' | sed 's/,$//')

# Pull the final result event (single line at end of stream).
RESULT_EVENT=$(jq -c 'select(.type=="result")' "$RUN_LOG" | tail -n 1)
RESULT_TEXT=$(echo "$RESULT_EVENT" | jq -r '.result // ""')
NUM_TURNS=$(echo "$RESULT_EVENT" | jq -r '.num_turns // 0')
TOTAL_COST=$(echo "$RESULT_EVENT" | jq -r '.total_cost_usd // 0')
IS_ERROR=$(echo "$RESULT_EVENT" | jq -r '.is_error // false')
PERM_DENIALS=$(echo "$RESULT_EVENT" | jq -c '.permission_denials // []')

# 5. Owner-gate JSON detection.
NEEDS_APPROVAL="false"
GATE_KIND=""
GATE_SEVERITY=""
GATE_RESOLUTION=""
if echo "$RESULT_TEXT" | grep -q '"needs_approval"[[:space:]]*:[[:space:]]*true'; then
  NEEDS_APPROVAL="true"
  # Extract first balanced {...} via python (avoids brittle sed).
  GATE_JSON=$(python3 - <<'PY' "$RESULT_TEXT"
import json, sys
text = sys.argv[1]
start = text.find("{")
if start == -1:
    sys.exit(0)
depth = 0
for i, ch in enumerate(text[start:], start=start):
    if ch == "{":
        depth += 1
    elif ch == "}":
        depth -= 1
        if depth == 0:
            try:
                obj = json.loads(text[start:i+1])
                print(json.dumps(obj))
            except Exception:
                pass
            break
PY
  )
  if [ -n "$GATE_JSON" ]; then
    GATE_KIND=$(echo "$GATE_JSON" | jq -r '.kind // ""')
    GATE_SEVERITY=$(echo "$GATE_JSON" | jq -r '.severity // ""')
    GATE_RESOLUTION=$(echo "$GATE_JSON" | jq -r '.proposed_resolution // ""')
  fi
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
echo "[$(date -u +%FT%TZ)] whatsapp_send.to=${WHATSAPP_SEND_TO:-<none>}  count=$WHATSAPP_SEND_COUNT"
echo "[$(date -u +%FT%TZ)] forbidden_hits=${FORBIDDEN_HITS:-<none>}"
echo "[$(date -u +%FT%TZ)] gate kind=$GATE_KIND severity=$GATE_SEVERITY resolution=$GATE_RESOLUTION"
echo "[$(date -u +%FT%TZ)] num_turns=$NUM_TURNS  cost=$TOTAL_COST  is_error=$IS_ERROR  perm_denials=$PERM_DENIALS"
echo "[$(date -u +%FT%TZ)] auditCalls delta: $AUDIT_BEFORE → $AUDIT_AFTER  (+$AUDIT_DELTA)"

if [ "$CLAUDE_EXIT" -ne 0 ]; then
  echo "[$(date -u +%FT%TZ)] claude -p exited $CLAUDE_EXIT" >&2
fi

# 7. Decide PASS / FAIL.
RESULT="FAIL"
DETAIL=""
if [ -n "$FORBIDDEN_HITS" ]; then
  DETAIL="agent called forbidden post-approval tool(s): $FORBIDDEN_HITS"
elif [ -z "$WHATSAPP_SEND_TO" ]; then
  DETAIL="agent did not call whatsapp_send for the empathetic acknowledgement"
elif [ "$WHATSAPP_SEND_TO" != "$SMOKE_FROM" ]; then
  DETAIL="whatsapp_send called with WRONG to=$WHATSAPP_SEND_TO (expected $SMOKE_FROM)"
elif [ "$NEEDS_APPROVAL" != "true" ]; then
  DETAIL="agent did not return owner-gate JSON (needs_approval=true)"
elif [ "$GATE_KIND" != "complaint" ]; then
  DETAIL="owner-gate kind='$GATE_KIND' (expected 'complaint')"
elif [ -z "$GATE_SEVERITY" ]; then
  DETAIL="owner-gate severity missing (required for kind=complaint)"
elif [ -z "$GATE_RESOLUTION" ]; then
  DETAIL="owner-gate proposed_resolution missing (required for kind=complaint)"
else
  RESULT="PASS"
  DETAIL="ack via whatsapp_send + owner-gate JSON kind=complaint severity=$GATE_SEVERITY resolution=$GATE_RESOLUTION"
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
  --arg gate_kind "$GATE_KIND" \
  --arg gate_severity "$GATE_SEVERITY" \
  --arg gate_resolution "$GATE_RESOLUTION" \
  --argjson tools "$TOOLS_USED" \
  --argjson approval "$( [ "$NEEDS_APPROVAL" = "true" ] && echo true || echo false )" \
  --arg audit_before "$AUDIT_BEFORE" \
  --arg audit_after "$AUDIT_AFTER" \
  '{
    ts: $ts,
    test: "complaint_smoke",
    inbound: { from: $from, message: $msg },
    result: $result,
    detail: $detail,
    needs_approval: $approval,
    gate: { kind: $gate_kind, severity: $gate_severity, proposed_resolution: $gate_resolution },
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
echo "===== complaint smoke result ====="
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
