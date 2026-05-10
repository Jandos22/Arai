#!/usr/bin/env bash
# verify_telegram_bots.sh — validate the four Arai Telegram bots without
# printing or committing bot tokens.
#
# Usage:
#   bash scripts/verify_telegram_bots.sh
#   bash scripts/verify_telegram_bots.sh --send-test
#
# Requires:
#   TELEGRAM_BOT_TOKEN_OWNER
#   TELEGRAM_BOT_TOKEN_SALES
#   TELEGRAM_BOT_TOKEN_OPS
#   TELEGRAM_BOT_TOKEN_MARKETING
#   TELEGRAM_OWNER_CHAT_ID

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

SEND_TEST=0

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/verify_telegram_bots.sh [--send-test]

Options:
  --send-test   Send a short validation message from each bot to
                TELEGRAM_OWNER_CHAT_ID after getMe succeeds.
  --help, -h    Show this help.

The script loads .env.local or ~/.config/arai/env.local via scripts/load_env.sh
and never prints bot tokens.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --send-test)
      SEND_TEST=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n\n' "$1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

red()    { printf '\033[31m%s\033[0m\n' "$*"; }
green()  { printf '\033[32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[33m%s\033[0m\n' "$*"; }
plain()  { printf '%s\n' "$*"; }

# shellcheck disable=SC1091
source scripts/load_env.sh
if ! arai_load_env "$repo_root"; then
  red "No env file found. Create .env.local or ~/.config/arai/env.local."
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  red "curl is required."
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  red "python3 is required for safe JSON parsing."
  exit 1
fi

required_vars=(
  TELEGRAM_BOT_TOKEN_OWNER
  TELEGRAM_BOT_TOKEN_SALES
  TELEGRAM_BOT_TOKEN_OPS
  TELEGRAM_BOT_TOKEN_MARKETING
  TELEGRAM_OWNER_CHAT_ID
)

missing=()
for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    missing+=("$var_name")
  fi
done

if (( ${#missing[@]} > 0 )); then
  red "Missing required Telegram env vars:"
  for var_name in "${missing[@]}"; do
    plain "  - $var_name"
  done
  exit 1
fi

if [[ ! "${TELEGRAM_OWNER_CHAT_ID}" =~ ^-?[0-9]+$ ]]; then
  red "TELEGRAM_OWNER_CHAT_ID must be numeric."
  exit 1
fi

api_call() {
  local token="$1"
  local method="$2"
  local payload="${3:-}"
  local url="https://api.telegram.org/bot${token}/${method}"

  if [[ -n "$payload" ]]; then
    curl -fsS \
      -H "Content-Type: application/json" \
      -d "$payload" \
      "$url"
  else
    curl -fsS "$url"
  fi
}

parse_get_me() {
  python3 -c '
import json
import sys

role = sys.argv[1]
try:
    data = json.load(sys.stdin)
except json.JSONDecodeError as exc:
    print(f"{role}: invalid JSON from Telegram: {exc}", file=sys.stderr)
    sys.exit(2)

if not data.get("ok"):
    desc = data.get("description") or "unknown Telegram API error"
    print(f"{role}: {desc}", file=sys.stderr)
    sys.exit(3)

result = data.get("result") or {}
username = result.get("username") or "(no username)"
first_name = result.get("first_name") or "(no display name)"
bot_id = result.get("id") or "?"
print(f"{role}: @{username} ({first_name}) id={bot_id}")
'
}

send_test_message() {
  local role="$1"
  local token="$2"
  local message
  message=$(python3 -c '
import json
import os
import sys

role = sys.argv[1]
chat_id = os.environ["TELEGRAM_OWNER_CHAT_ID"]
text = f"Arai Telegram verification passed for {role}."
print(json.dumps({"chat_id": chat_id, "text": text}))
' "$role")

  api_call "$token" "sendMessage" "$message" | python3 -c '
import json
import sys

role = sys.argv[1]
data = json.load(sys.stdin)
if not data.get("ok"):
    desc = data.get("description") or "unknown Telegram API error"
    print(f"{role}: sendMessage failed: {desc}", file=sys.stderr)
    sys.exit(4)
print(f"{role}: test message sent")
' "$role"
}

roles=(
  "owner:TELEGRAM_BOT_TOKEN_OWNER"
  "sales:TELEGRAM_BOT_TOKEN_SALES"
  "ops:TELEGRAM_BOT_TOKEN_OPS"
  "marketing:TELEGRAM_BOT_TOKEN_MARKETING"
)

plain "=== Arai Telegram Bot Verification ==="
plain "env=${ARAI_ENV_FILE_LOADED}"
plain ""

yellow "[1/2] Validate bot tokens with getMe"
for role_spec in "${roles[@]}"; do
  role="${role_spec%%:*}"
  token_var="${role_spec#*:}"
  token="${!token_var}"
  api_call "$token" "getMe" | parse_get_me "$role"
done
green "All bot tokens are valid."

if [[ "$SEND_TEST" -eq 1 ]]; then
  plain ""
  yellow "[2/2] Send test messages to TELEGRAM_OWNER_CHAT_ID"
  for role_spec in "${roles[@]}"; do
    role="${role_spec%%:*}"
    token_var="${role_spec#*:}"
    token="${!token_var}"
    send_test_message "$role" "$token"
  done
  green "All test messages sent."
else
  plain ""
  yellow "[2/2] Send test messages skipped"
  plain "Run with --send-test after messaging each bot once from the owner account."
fi
