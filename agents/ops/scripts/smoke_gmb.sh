#!/usr/bin/env bash
# Ops Agent — GMB review-reply smoke.
#
# 1. Source repo .env.local for STEPPE_MCP_URL / STEPPE_MCP_TOKEN.
# 2. Snapshot the sandbox audit-call counter via evaluator_get_evidence_summary.
# 3. List reviews + recorded replies; pick the highest-rated unreplied review
#    (or fall back to the most recent review if all are replied to).
# 4. Run `claude -p` from agents/ops/ with the GMB-review prompt template,
#    in stream-json mode so we can capture every tool_use the model makes.
# 5. PASS when EITHER:
#      - the agent's stream contained a tool_use for
#        mcp__happycake__gb_simulate_reply with reviewId == picked id, OR
#      - the agent returned the owner-gate JSON (rating ≤ 2 path).
# 6. Append one summary row to evidence/ops-sample.jsonl, print PASS/FAIL.
#
# Usage:
#   bash agents/ops/scripts/smoke_gmb.sh
#   bash agents/ops/scripts/smoke_gmb.sh rev_003   # force a specific review
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

LOG_DIR="$REPO_ROOT/evidence"
mkdir -p "$LOG_DIR"
RUN_LOG="$LOG_DIR/ops-gmb-smoke-$(date -u +%Y%m%dT%H%M%SZ).log"
SAMPLE_OUT="$LOG_DIR/ops-sample.jsonl"

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

# 2. Pick a review to reply to.
REVIEWS_JSON=$(mcp_call gb_list_reviews '{}' | jq -r '.result.content[0].text')
ACTIONS_JSON=$(mcp_call gb_list_simulated_actions '{}' | jq -r '.result.content[0].text')

PICK_ID="${1:-}"
if [ -z "$PICK_ID" ]; then
  # Highest-rated review without an existing reply, falling back to most recent.
  PICK_ID=$(jq -nr \
    --argjson reviews "$REVIEWS_JSON" \
    --argjson actions "$ACTIONS_JSON" '
      ($actions.replies // []) | map(.reviewId) as $replied
      | $reviews | map(select(.id as $rid | $replied | index($rid) | not))
      | (if length > 0 then sort_by(-.rating, .createdAt) else $reviews | sort_by(.createdAt) | reverse end)
      | .[0].id // empty
    ')
fi

if [ -z "$PICK_ID" ]; then
  echo "error: could not pick a review id from gb_list_reviews" >&2
  exit 1
fi

PICK=$(jq -nc --argjson reviews "$REVIEWS_JSON" --arg id "$PICK_ID" \
  '$reviews | map(select(.id == $id)) | .[0] // {}')
RATING=$(echo "$PICK" | jq -r '.rating // 0')
AUTHOR=$(echo "$PICK" | jq -r '.author // "friend"')
TEXT=$(echo "$PICK" | jq -r '.text // ""')

echo "[$(date -u +%FT%TZ)] picked $PICK_ID  rating=$RATING  author=$AUTHOR"
echo "[$(date -u +%FT%TZ)]   text=$TEXT"

# 3. Build the prompt by filling the template.
PROMPT_TEMPLATE="$(cat "$AGENT_DIR/PROMPTS/gmb_review.md")"
PROMPT="${PROMPT_TEMPLATE//'{{review_id}}'/$PICK_ID}"
PROMPT="${PROMPT//'{{rating}}'/$RATING}"
PROMPT="${PROMPT//'{{author}}'/$AUTHOR}"
PROMPT="${PROMPT//'{{review_text}}'/$TEXT}"

# 4. Run the agent with stream-json so we can see every tool_use.
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

# 5. Parse the stream for tool_use names + the final result text.
TOOLS_USED=$(jq -c -r '
  select(.type=="assistant") | .message.content[]? |
  select(.type=="tool_use") | .name
' "$RUN_LOG" | sort -u | jq -R . | jq -sc .)

GB_REPLY_REVIEW_ID=$(jq -r '
  select(.type=="assistant") | .message.content[]? |
  select(.type=="tool_use" and .name=="mcp__happycake__gb_simulate_reply") |
  .input.reviewId
' "$RUN_LOG" | head -n 1)

GB_REPLY_BODY=$(jq -r '
  select(.type=="assistant") | .message.content[]? |
  select(.type=="tool_use" and .name=="mcp__happycake__gb_simulate_reply") |
  .input.reply
' "$RUN_LOG" | head -n 1)

# Pull the final result event (single line at end of stream).
RESULT_EVENT=$(jq -c 'select(.type=="result")' "$RUN_LOG" | tail -n 1)
RESULT_TEXT=$(echo "$RESULT_EVENT" | jq -r '.result // ""')
NUM_TURNS=$(echo "$RESULT_EVENT" | jq -r '.num_turns // 0')
TOTAL_COST=$(echo "$RESULT_EVENT" | jq -r '.total_cost_usd // 0')
IS_ERROR=$(echo "$RESULT_EVENT" | jq -r '.is_error // false')
PERM_DENIALS=$(echo "$RESULT_EVENT" | jq -c '.permission_denials // []')

# 6. Detect owner-gate path (final result is a JSON object with needs_approval).
NEEDS_APPROVAL="false"
if echo "$RESULT_TEXT" | grep -q '"needs_approval"[[:space:]]*:[[:space:]]*true'; then
  NEEDS_APPROVAL="true"
fi

# 7. Post-run audit-call delta.
AUDIT_AFTER=$(mcp_call evaluator_get_evidence_summary '{}' \
  | jq -r '.result.content[0].text' | jq -r '.counts.auditCalls // 0')
AUDIT_DELTA=$(( AUDIT_AFTER - AUDIT_BEFORE ))

echo
echo "----- agent reply (truncated) -----"
echo "$RESULT_TEXT" | head -c 1200
echo
echo "-----------------------------------"
echo "[$(date -u +%FT%TZ)] tools_used=$TOOLS_USED"
echo "[$(date -u +%FT%TZ)] gb_simulate_reply.reviewId=${GB_REPLY_REVIEW_ID:-<none>}"
echo "[$(date -u +%FT%TZ)] num_turns=$NUM_TURNS  cost=$TOTAL_COST  is_error=$IS_ERROR  perm_denials=$PERM_DENIALS"
echo "[$(date -u +%FT%TZ)] auditCalls delta: $AUDIT_BEFORE → $AUDIT_AFTER  (+$AUDIT_DELTA)"

if [ "$CLAUDE_EXIT" -ne 0 ]; then
  echo "[$(date -u +%FT%TZ)] claude -p exited $CLAUDE_EXIT" >&2
fi

# 8. Decide PASS / FAIL.
RESULT="FAIL"
DETAIL=""
if [ -n "$GB_REPLY_REVIEW_ID" ] && [ "$GB_REPLY_REVIEW_ID" = "$PICK_ID" ]; then
  RESULT="PASS"
  DETAIL="gb_simulate_reply called with reviewId=$PICK_ID"
elif [ -n "$GB_REPLY_REVIEW_ID" ]; then
  RESULT="FAIL"
  DETAIL="gb_simulate_reply called with WRONG reviewId=$GB_REPLY_REVIEW_ID (expected $PICK_ID)"
elif [ "$NEEDS_APPROVAL" = "true" ]; then
  if [ "$RATING" -le 2 ]; then
    RESULT="PASS"
    DETAIL="owner-gate JSON returned for rating=$RATING (review_low_rating) — by design no gb_simulate_reply"
  else
    RESULT="FAIL"
    DETAIL="owner-gate JSON returned for rating=$RATING but no trigger should have fired"
  fi
else
  RESULT="FAIL"
  DETAIL="agent did not call gb_simulate_reply and did not return needs_approval JSON"
fi

# 9. Append one structured row to evidence/ops-sample.jsonl.
TS=$(date -u +%FT%TZ)
REPLY_PREVIEW=$(echo "${GB_REPLY_BODY:-}" | tr '\n' ' ' | head -c 280 \
  | sed -E 's/[A-Za-z0-9]{32,}/<REDACTED>/g')
RESPONSE_PREVIEW=$(echo "$RESULT_TEXT" | tr '\n' ' ' | head -c 280 \
  | sed -E 's/[A-Za-z0-9]{32,}/<REDACTED>/g')

SAMPLE_ROW=$(jq -nc \
  --arg ts "$TS" \
  --arg review_id "$PICK_ID" \
  --arg rating "$RATING" \
  --arg author "$AUTHOR" \
  --arg result "$RESULT" \
  --arg detail "$DETAIL" \
  --arg reply_preview "$REPLY_PREVIEW" \
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
    test: "ops_gmb_review_smoke",
    review: { id: $review_id, rating: ($rating | tonumber), author: $author },
    result: $result,
    detail: $detail,
    needs_approval: $approval,
    tools_used: $tools,
    reply_preview: $reply_preview,
    response_preview: $preview,
    num_turns: ($num_turns | tonumber),
    total_cost_usd: ($cost | tonumber),
    is_error: ($is_error == "true"),
    audit_calls_before: ($audit_before | tonumber),
    audit_calls_after: ($audit_after | tonumber)
  }')
echo "$SAMPLE_ROW" >> "$SAMPLE_OUT"

echo
echo "===== ops gmb smoke result ====="
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
