#!/usr/bin/env bash
# evaluator_preview.sh — fetch the four evaluator_score_* responses + the
# combined team report against the live sandbox. Designed to run AFTER all
# the agents have done some work, so the scores are meaningful.
#
# Usage:
#   bash scripts/evaluator_preview.sh
#
# Requires:
#   .env.local or ~/.config/arai/env.local with STEPPE_MCP_TOKEN
#   curl, jq
#
# Output: prints a compact summary to stdout AND writes the full responses to
# evidence/evaluator-preview-<timestamp>.json. The summary is what you paste
# into Telegram for a quick "where do we stand" check; the JSON is the source
# of truth.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

# shellcheck disable=SC1091
source scripts/load_env.sh
arai_load_env "$repo_root" || true

: "${STEPPE_MCP_TOKEN:?STEPPE_MCP_TOKEN not set in .env.local, ARAI_ENV_FILE, or ~/.config/arai/env.local}"
: "${STEPPE_MCP_URL:=https://www.steppebusinessclub.com/api/mcp}"

mkdir -p evidence
ts="$(date -u +%Y%m%dT%H%M%SZ)"
out="evidence/evaluator-preview-${ts}.json"

# Helper: call a tool, return the JSON-decoded `result.content[0].text` payload.
call_tool() {
  local tool="$1"
  local args="${2:-}"
  if [[ -z "$args" ]]; then
    args="{}"
  fi
  local body
  body=$(jq -n \
    --arg method "tools/call" \
    --arg name "$tool" \
    --argjson args "$args" \
    '{jsonrpc:"2.0", id: (now|floor), method:$method, params:{name:$name, arguments:$args}}')
  curl -sS \
    -H "X-Team-Token: ${STEPPE_MCP_TOKEN}" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -d "$body" \
    "$STEPPE_MCP_URL" \
    | jq -r '.result.content[0].text // empty' \
    | jq '.'
}

echo "Calling evaluator tools against $STEPPE_MCP_URL …" >&2

ev_summary=$(call_tool evaluator_get_evidence_summary)
sc_marketing=$(call_tool evaluator_score_marketing_loop)
sc_pos=$(call_tool evaluator_score_pos_kitchen_flow)
sc_channel=$(call_tool evaluator_score_channel_response)
sc_world=$(call_tool evaluator_score_world_scenario)
team_report=$(call_tool evaluator_generate_team_report \
  '{"repoUrl":"https://github.com/Jandos22/Arai","notes":"Arai - Jan Solo team, hackathon submission preview"}')

jq -n \
  --argjson evidence "$ev_summary" \
  --argjson marketing "$sc_marketing" \
  --argjson pos_kitchen "$sc_pos" \
  --argjson channels "$sc_channel" \
  --argjson world "$sc_world" \
  --argjson team_report "$team_report" \
  --arg ts "$ts" \
  '{ts:$ts, evidence:$evidence, scores:{marketing:$marketing, pos_kitchen:$pos_kitchen, channels:$channels, world:$world}, team_report:$team_report}' \
  > "$out"

echo "Wrote $out"
echo
echo "=== EVALUATOR PREVIEW @ $ts ==="
jq -r '
  "marketing       : " + (.scores.marketing.score // .scores.marketing | tostring),
  "pos_kitchen     : " + (.scores.pos_kitchen.score // .scores.pos_kitchen | tostring),
  "channels        : " + (.scores.channels.score // .scores.channels | tostring),
  "world           : " + (.scores.world.score // .scores.world | tostring)
' "$out"
echo
echo "(full payload at $out)"
