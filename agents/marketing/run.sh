#!/usr/bin/env bash
# Marketing Agent — one-shot driver.
#
# Loads the sandbox token, invokes `claude -p` against this folder's CLAUDE.md
# + .mcp.json, captures stdout to a per-run log, and extracts the evidence
# block to evidence/marketing.jsonl + a redacted ≤20-line sample.
#
# Usage:
#   agents/marketing/run.sh
# Requirements:
#   - .env.local, ARAI_ENV_FILE, or ~/.config/arai/env.local with STEPPE_MCP_TOKEN
#   - claude CLI on PATH (Claude Code v2.x)

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"

if [ ! -f "$REPO_ROOT/scripts/load_env.sh" ]; then
  echo "error: env helper missing at $REPO_ROOT/scripts/load_env.sh" >&2
  exit 1
fi

# shellcheck disable=SC1091
source "$REPO_ROOT/scripts/load_env.sh"
if ! arai_load_env "$REPO_ROOT"; then
  echo "error: env missing — create .env.local or ~/.config/arai/env.local with STEPPE_MCP_TOKEN" >&2
  exit 1
fi

if [ -z "${STEPPE_MCP_TOKEN:-}" ]; then
  echo "error: STEPPE_MCP_TOKEN not set after loading env" >&2
  exit 1
fi

LOG_DIR="$REPO_ROOT/evidence"
mkdir -p "$LOG_DIR"
RUN_LOG="$LOG_DIR/marketing-run-$(date -u +%Y%m%dT%H%M%SZ).log"

PROMPT="$(cat "$HERE/PROMPT.md")"

cd "$HERE"
echo "[$(date -u +%FT%TZ)] launching marketing agent → $RUN_LOG" >&2

# bypassPermissions: the role contract in CLAUDE.md polices the tool surface;
# we don't enumerate per-tool flags here because the agent's allowed list is
# longer than the CLI ergonomics support cleanly.
claude -p "$PROMPT" \
  --permission-mode bypassPermissions \
  | tee "$RUN_LOG"

EVIDENCE_OUT="$LOG_DIR/marketing.jsonl"
SAMPLE_OUT="$LOG_DIR/marketing-sample.jsonl"

awk '
  /--- EVIDENCE BEGIN ---/ { flag=1; next }
  /--- EVIDENCE END ---/   { flag=0 }
  flag
' "$RUN_LOG" > "$EVIDENCE_OUT" || true

# Redacted sample: last 20 evidence lines. Defense-in-depth scrub for any
# long base64-ish run (no underscores / hyphens, so snake_case tool names
# like marketing_launch_simulated_campaign survive).
tail -n 20 "$EVIDENCE_OUT" 2>/dev/null \
  | sed -E 's/[A-Za-z0-9]{32,}/<REDACTED>/g' \
  > "$SAMPLE_OUT" || true

echo
echo "[$(date -u +%FT%TZ)] wrote $EVIDENCE_OUT ($(wc -l < "$EVIDENCE_OUT" | tr -d ' ') lines)"
echo "[$(date -u +%FT%TZ)] wrote $SAMPLE_OUT ($(wc -l < "$SAMPLE_OUT" | tr -d ' ') lines)"
