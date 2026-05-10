#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

# shellcheck source=../load_env.sh
source scripts/load_env.sh
arai_load_env "$repo_root" >/dev/null || true

: "${STEPPE_MCP_URL:?STEPPE_MCP_URL not loaded}"
: "${STEPPE_MCP_TOKEN:?STEPPE_MCP_TOKEN not loaded}"

mcp_call() {
  local tool="${1:?tool required}"
  local args
  if [[ $# -ge 2 ]]; then
    args="$2"
  else
    args="{}"
  fi
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

latest_orchestrator_evidence() {
  ls -t evidence/orchestrator-*.jsonl 2>/dev/null | head -1
}

wait_for_persona_evidence() {
  local marker="${1:?marker required}"
  local label="${2:?label required}"
  local cap="${PERSONA_WAIT_SECONDS:-120}"
  local start_epoch
  start_epoch="$(date +%s)"

  while (( "$(date +%s)" - start_epoch < cap )); do
    local latest
    latest="$(latest_orchestrator_evidence || true)"
    if [[ -n "$latest" ]] && grep -Fq "$marker" "$latest"; then
      if grep -Eq '"kind": "(scenario_summary|webhook_inbound|channel_inbound)"' "$latest"; then
        printf '%s\n' "$latest"
        return 0
      fi
    fi
    sleep 2
  done

  echo "Timed out waiting for ${label} evidence marker (${marker})" >&2
  return 1
}
