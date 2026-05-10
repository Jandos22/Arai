#!/usr/bin/env bash
# Ops Agent — Instagram post approval-flow smoke. The money shot.
#
# Three stages, mirroring the canonical owner-gate pattern:
#
# STAGE 1 — propose
#   * Run `claude -p` with PROMPTS/ig_post_proposal.md, stage=propose, against
#     a kitchen-driven trigger ("we have honey cake today").
#   * Verify the agent called mcp__happycake__instagram_schedule_post.
#   * Verify the agent's final result is owner-gate JSON with
#     trigger="ig_post_publish" and a non-empty ref_id (scheduledPostId).
#
# STAGE 2 — owner approval (simulated)
#   * Harness directly calls instagram_approve_post(scheduledPostId).
#   * In production this would be the orchestrator's Telegram inline-keyboard
#     callback. Sandbox returns success.
#
# STAGE 3 — publish
#   * Run `claude -p` again with PROMPTS/ig_post_proposal.md, stage=publish,
#     scheduled_post_id from stage 1.
#   * Verify the agent called mcp__happycake__instagram_publish_post with the
#     same scheduledPostId.
#
# All three stages must PASS, otherwise the smoke is FAIL.
#
# Usage:
#   bash agents/ops/scripts/smoke_ig_post.sh
#   bash agents/ops/scripts/smoke_ig_post.sh "we have whole honey cakes ready, $42 each"
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
PROPOSE_LOG="$LOG_DIR/ops-igpost-propose-$TS_RUN.log"
PUBLISH_LOG="$LOG_DIR/ops-igpost-publish-$TS_RUN.log"
SAMPLE_OUT="$LOG_DIR/ops-sample.jsonl"

DEFAULT_TRIGGER_DETAIL="Today's bake includes whole cake \"Honey\", 1.2 kg, \$42, ready by noon. Pistachio Roll also out, by the slice."
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

# 0. Pre-run audit-call snapshot.
AUDIT_BEFORE=$(mcp_call evaluator_get_evidence_summary '{}' \
  | jq -r '.result.content[0].text' | jq -r '.counts.auditCalls // 0')
echo "[$(date -u +%FT%TZ)] auditCalls before: $AUDIT_BEFORE"

# ============================== STAGE 1 — propose ==============================
echo
echo "===== stage 1 — propose ====="
PROPOSE_TEMPLATE="$(cat "$AGENT_DIR/PROMPTS/ig_post_proposal.md")"
PROPOSE_PROMPT="${PROPOSE_TEMPLATE//'{{stage}}'/propose}"
PROPOSE_PROMPT="${PROPOSE_PROMPT//'{{trigger}}'/kitchen_today_bake}"
PROPOSE_PROMPT="${PROPOSE_PROMPT//'{{trigger_detail}}'/$TRIGGER_DETAIL}"
PROPOSE_PROMPT="${PROPOSE_PROMPT//'{{scheduled_post_id}}'/}"

echo "[$(date -u +%FT%TZ)] launching claude -p (propose)"
run_claude_stream "$PROPOSE_PROMPT" "$PROPOSE_LOG" || \
  echo "[$(date -u +%FT%TZ)] claude -p (propose) exited non-zero" >&2

PROPOSE_TOOLS=$(jq -c -r '
  select(.type=="assistant") | .message.content[]? |
  select(.type=="tool_use") | .name
' "$PROPOSE_LOG" | sort -u | jq -R . | jq -sc .)

SCHEDULE_TOOL_INPUT=$(jq -c '
  select(.type=="assistant") | .message.content[]? |
  select(.type=="tool_use" and .name=="mcp__happycake__instagram_schedule_post") |
  .input
' "$PROPOSE_LOG" | head -n 1)

PROPOSE_RESULT_EVENT=$(jq -c 'select(.type=="result")' "$PROPOSE_LOG" | tail -n 1)
PROPOSE_RESULT_TEXT=$(echo "$PROPOSE_RESULT_EVENT" | jq -r '.result // ""')
PROPOSE_NUM_TURNS=$(echo "$PROPOSE_RESULT_EVENT" | jq -r '.num_turns // 0')

# Owner-gate JSON should be the only top-level object in the result text.
OWNER_GATE_JSON=$(echo "$PROPOSE_RESULT_TEXT" | python3 -c '
import json, re, sys
text = sys.stdin.read()
# Walk the first balanced { ... } block (mirrors orchestrator _extract_json).
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
            blob = text[start:i+1]
            try:
                obj = json.loads(blob)
                print(json.dumps(obj))
                sys.exit(0)
            except json.JSONDecodeError:
                start = -1
                continue
sys.exit(0)
')
SCHEDULED_POST_ID=$(echo "$OWNER_GATE_JSON" | jq -r '.ref_id // empty')
GATE_TRIGGER=$(echo "$OWNER_GATE_JSON" | jq -r '.trigger // empty')
GATE_NEEDS_APPROVAL=$(echo "$OWNER_GATE_JSON" | jq -r '.needs_approval // false')

# Cross-check with the actual scheduled_post_id returned to the agent. Tolerant
# of grep finding nothing — pipefail would otherwise kill the script.
SCHEDULE_RETURN_ID=""
TOOL_RESULTS_TEXT=$(jq -c -r '
  select(.type=="user") | .message.content[]? |
  select(.type=="tool_result") | .content[]? |
  select(.type=="text") | .text
' "$PROPOSE_LOG" || true)
if [ -n "$TOOL_RESULTS_TEXT" ]; then
  SCHEDULE_RETURN_ID=$(printf '%s\n' "$TOOL_RESULTS_TEXT" \
    | grep -o '"scheduledPostId":"[^"]*"' \
    | head -n 1 \
    | sed 's/.*"scheduledPostId":"\([^"]*\)".*/\1/' || true)
fi

echo "[$(date -u +%FT%TZ)] propose tools_used=$PROPOSE_TOOLS"
echo "[$(date -u +%FT%TZ)] propose schedule_input=${SCHEDULE_TOOL_INPUT:-<none>}"
echo "[$(date -u +%FT%TZ)] propose schedule_return_id=${SCHEDULE_RETURN_ID:-<none>}"
echo "[$(date -u +%FT%TZ)] propose gate ref_id=${SCHEDULED_POST_ID:-<none>}  trigger=${GATE_TRIGGER:-<none>}  needs_approval=$GATE_NEEDS_APPROVAL"

STAGE1_PASS="false"
STAGE1_DETAIL=""
if [ -n "$SCHEDULE_TOOL_INPUT" ] \
   && [ "$GATE_NEEDS_APPROVAL" = "true" ] \
   && [ "$GATE_TRIGGER" = "ig_post_publish" ] \
   && [ -n "$SCHEDULED_POST_ID" ]; then
  STAGE1_PASS="true"
  STAGE1_DETAIL="instagram_schedule_post called; owner-gate JSON returned with ref_id=$SCHEDULED_POST_ID"
elif [ -z "$SCHEDULE_TOOL_INPUT" ]; then
  STAGE1_DETAIL="agent did not call instagram_schedule_post"
elif [ "$GATE_NEEDS_APPROVAL" != "true" ]; then
  STAGE1_DETAIL="agent did not return owner-gate JSON (needs_approval=$GATE_NEEDS_APPROVAL)"
elif [ "$GATE_TRIGGER" != "ig_post_publish" ]; then
  STAGE1_DETAIL="owner-gate JSON had wrong trigger=$GATE_TRIGGER"
else
  STAGE1_DETAIL="owner-gate JSON missing ref_id"
fi
echo "[$(date -u +%FT%TZ)] stage 1: $( [ "$STAGE1_PASS" = "true" ] && echo PASS || echo FAIL ) — $STAGE1_DETAIL"

# Sanity: gate ref_id should match the actual scheduledPostId returned to the agent.
if [ -n "$SCHEDULED_POST_ID" ] && [ -n "$SCHEDULE_RETURN_ID" ] \
   && [ "$SCHEDULED_POST_ID" != "$SCHEDULE_RETURN_ID" ]; then
  STAGE1_PASS="false"
  STAGE1_DETAIL="$STAGE1_DETAIL; ref_id ($SCHEDULED_POST_ID) != schedule_return_id ($SCHEDULE_RETURN_ID)"
  echo "[$(date -u +%FT%TZ)] stage 1: FAIL — $STAGE1_DETAIL" >&2
fi

# ============================== STAGE 2 — owner approval (simulated) ==============================
echo
echo "===== stage 2 — owner approval (simulated) ====="
STAGE2_PASS="false"
STAGE2_DETAIL="skipped (stage 1 did not yield a scheduledPostId)"
APPROVE_RESPONSE=""
if [ "$STAGE1_PASS" = "true" ]; then
  APPROVE_PAYLOAD=$(jq -nc --arg id "$SCHEDULED_POST_ID" '{scheduledPostId:$id}')
  APPROVE_RESPONSE=$(mcp_call instagram_approve_post "$APPROVE_PAYLOAD" \
    | jq -r '.result.content[0].text')
  APPROVE_STATUS=$(echo "$APPROVE_RESPONSE" | jq -r '.status // empty' 2>/dev/null || echo "")
  if [ "$APPROVE_STATUS" = "approved" ]; then
    STAGE2_PASS="true"
    STAGE2_DETAIL="instagram_approve_post → status=approved (scheduledPostId=$SCHEDULED_POST_ID)"
  else
    STAGE2_DETAIL="instagram_approve_post returned: $APPROVE_RESPONSE"
  fi
fi
echo "[$(date -u +%FT%TZ)] stage 2: $( [ "$STAGE2_PASS" = "true" ] && echo PASS || echo FAIL ) — $STAGE2_DETAIL"

# ============================== STAGE 3 — publish ==============================
echo
echo "===== stage 3 — publish ====="
STAGE3_PASS="false"
STAGE3_DETAIL="skipped (stage 2 did not record approval)"
PUBLISH_TOOLS="[]"
PUBLISH_RESULT_TEXT=""
PUBLISH_NUM_TURNS=0

if [ "$STAGE2_PASS" = "true" ]; then
  PUBLISH_TEMPLATE="$(cat "$AGENT_DIR/PROMPTS/ig_post_proposal.md")"
  PUBLISH_PROMPT="${PUBLISH_TEMPLATE//'{{stage}}'/publish}"
  PUBLISH_PROMPT="${PUBLISH_PROMPT//'{{trigger}}'/kitchen_today_bake}"
  PUBLISH_PROMPT="${PUBLISH_PROMPT//'{{trigger_detail}}'/$TRIGGER_DETAIL}"
  PUBLISH_PROMPT="${PUBLISH_PROMPT//'{{scheduled_post_id}}'/$SCHEDULED_POST_ID}"

  echo "[$(date -u +%FT%TZ)] launching claude -p (publish)"
  run_claude_stream "$PUBLISH_PROMPT" "$PUBLISH_LOG" || \
    echo "[$(date -u +%FT%TZ)] claude -p (publish) exited non-zero" >&2

  PUBLISH_TOOLS=$(jq -c -r '
    select(.type=="assistant") | .message.content[]? |
    select(.type=="tool_use") | .name
  ' "$PUBLISH_LOG" | sort -u | jq -R . | jq -sc .)

  PUBLISH_TOOL_INPUT=$(jq -c '
    select(.type=="assistant") | .message.content[]? |
    select(.type=="tool_use" and .name=="mcp__happycake__instagram_publish_post") |
    .input
  ' "$PUBLISH_LOG" | head -n 1)

  PUBLISH_TOOL_ID=$(echo "$PUBLISH_TOOL_INPUT" | jq -r '.scheduledPostId // empty')

  PUBLISH_RESULT_EVENT=$(jq -c 'select(.type=="result")' "$PUBLISH_LOG" | tail -n 1)
  PUBLISH_RESULT_TEXT=$(echo "$PUBLISH_RESULT_EVENT" | jq -r '.result // ""')
  PUBLISH_NUM_TURNS=$(echo "$PUBLISH_RESULT_EVENT" | jq -r '.num_turns // 0')

  echo "[$(date -u +%FT%TZ)] publish tools_used=$PUBLISH_TOOLS"
  echo "[$(date -u +%FT%TZ)] publish input.scheduledPostId=${PUBLISH_TOOL_ID:-<none>}"

  if [ -n "$PUBLISH_TOOL_ID" ] && [ "$PUBLISH_TOOL_ID" = "$SCHEDULED_POST_ID" ]; then
    STAGE3_PASS="true"
    STAGE3_DETAIL="instagram_publish_post called with scheduledPostId=$SCHEDULED_POST_ID"
  elif [ -n "$PUBLISH_TOOL_ID" ]; then
    STAGE3_DETAIL="instagram_publish_post called with WRONG scheduledPostId=$PUBLISH_TOOL_ID (expected $SCHEDULED_POST_ID)"
  else
    STAGE3_DETAIL="agent did not call instagram_publish_post"
  fi
fi
echo "[$(date -u +%FT%TZ)] stage 3: $( [ "$STAGE3_PASS" = "true" ] && echo PASS || echo FAIL ) — $STAGE3_DETAIL"

# ============================== Aggregate result ==============================
AUDIT_AFTER=$(mcp_call evaluator_get_evidence_summary '{}' \
  | jq -r '.result.content[0].text' | jq -r '.counts.auditCalls // 0')
AUDIT_DELTA=$(( AUDIT_AFTER - AUDIT_BEFORE ))
echo
echo "[$(date -u +%FT%TZ)] auditCalls delta: $AUDIT_BEFORE → $AUDIT_AFTER  (+$AUDIT_DELTA)"

OVERALL="FAIL"
if [ "$STAGE1_PASS" = "true" ] && [ "$STAGE2_PASS" = "true" ] && [ "$STAGE3_PASS" = "true" ]; then
  OVERALL="PASS"
fi

# Append one structured row to evidence/ops-sample.jsonl.
TS=$(date -u +%FT%TZ)
GATE_DRAFT_PREVIEW=$(echo "$OWNER_GATE_JSON" | jq -r '.draft // ""' \
  | tr '\n' ' ' | head -c 280 | sed -E 's/[A-Za-z0-9]{32,}/<REDACTED>/g')
PUBLISH_PREVIEW=$(echo "$PUBLISH_RESULT_TEXT" | tr '\n' ' ' | head -c 280 \
  | sed -E 's/[A-Za-z0-9]{32,}/<REDACTED>/g')

SAMPLE_ROW=$(jq -nc \
  --arg ts "$TS" \
  --arg trigger_detail "$TRIGGER_DETAIL" \
  --arg result "$OVERALL" \
  --arg s1 "$STAGE1_PASS" --arg s1d "$STAGE1_DETAIL" \
  --arg s2 "$STAGE2_PASS" --arg s2d "$STAGE2_DETAIL" \
  --arg s3 "$STAGE3_PASS" --arg s3d "$STAGE3_DETAIL" \
  --arg post_id "$SCHEDULED_POST_ID" \
  --arg gate_trigger "$GATE_TRIGGER" \
  --arg gate_draft "$GATE_DRAFT_PREVIEW" \
  --arg publish_preview "$PUBLISH_PREVIEW" \
  --argjson propose_tools "$PROPOSE_TOOLS" \
  --argjson publish_tools "$PUBLISH_TOOLS" \
  --arg audit_before "$AUDIT_BEFORE" \
  --arg audit_after "$AUDIT_AFTER" \
  --arg propose_turns "$PROPOSE_NUM_TURNS" \
  --arg publish_turns "$PUBLISH_NUM_TURNS" \
  '{
    ts: $ts,
    test: "ops_ig_post_owner_gate_smoke",
    trigger_detail: $trigger_detail,
    result: $result,
    stages: {
      propose: { pass: ($s1=="true"), detail: $s1d, tools_used: $propose_tools, num_turns: ($propose_turns | tonumber) },
      owner_approval: { pass: ($s2=="true"), detail: $s2d },
      publish: { pass: ($s3=="true"), detail: $s3d, tools_used: $publish_tools, num_turns: ($publish_turns | tonumber) }
    },
    scheduled_post_id: $post_id,
    gate_trigger: $gate_trigger,
    gate_draft_preview: $gate_draft,
    publish_preview: $publish_preview,
    audit_calls_before: ($audit_before | tonumber),
    audit_calls_after: ($audit_after | tonumber)
  }')
echo "$SAMPLE_ROW" >> "$SAMPLE_OUT"

echo
echo "===== ops ig_post smoke result ====="
echo "$OVERALL  stage1=$STAGE1_PASS stage2=$STAGE2_PASS stage3=$STAGE3_PASS"
echo "propose log: $PROPOSE_LOG"
echo "publish log: ${PUBLISH_LOG:-<not run>}"
echo "sample:      $SAMPLE_OUT"
echo "row:"
echo "  $SAMPLE_ROW"

if [ "$OVERALL" = "PASS" ]; then
  exit 0
else
  exit 1
fi
