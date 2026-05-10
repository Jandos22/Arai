#!/usr/bin/env bash
# Register sandbox WhatsApp and Instagram webhook endpoints.
#
# The live path calls the Steppe MCP registration tools through
# orchestrator.main. The dry-run path prints the exact tool names and URLs
# without requiring STEPPE_MCP_TOKEN or making network calls.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

DRY_RUN=0
BASE_URL="${PUBLIC_WEBHOOK_BASE_URL:-}"
PYTHON="${PYTHON:-orchestrator/.venv/bin/python}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/register_webhooks.sh [--dry-run] [--base-url https://TUNNEL]

Environment:
  PUBLIC_WEBHOOK_BASE_URL  Public HTTPS tunnel base URL, such as
                           https://example.trycloudflare.com
  STEPPE_MCP_TOKEN         Required only for live registration
  PYTHON                   Optional Python path (default orchestrator/.venv/bin/python)

Examples:
  PUBLIC_WEBHOOK_BASE_URL=https://example.trycloudflare.com \
    bash scripts/register_webhooks.sh --dry-run

  bash scripts/register_webhooks.sh --base-url https://example.ngrok-free.app
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --base-url)
      if [[ $# -lt 2 || -z "${2:-}" ]]; then
        printf '%s\n\n' '--base-url requires a value.' >&2
        usage >&2
        exit 1
      fi
      BASE_URL="${2:-}"
      shift 2
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

# shellcheck disable=SC1091
source scripts/load_env.sh
arai_load_env "$repo_root" >/dev/null 2>&1 || true

# Re-read after env loading, but preserve explicit --base-url.
if [[ -z "$BASE_URL" ]]; then
  BASE_URL="${PUBLIC_WEBHOOK_BASE_URL:-}"
fi

if [[ -z "$BASE_URL" ]]; then
  printf 'PUBLIC_WEBHOOK_BASE_URL is required. Set it or pass --base-url.\n' >&2
  exit 1
fi

BASE_URL="${BASE_URL%/}"
if [[ "$BASE_URL" != https://* ]]; then
  printf 'PUBLIC_WEBHOOK_BASE_URL must be an HTTPS tunnel URL, got: %s\n' "$BASE_URL" >&2
  exit 1
fi

wa_url="${BASE_URL}/webhooks/whatsapp"
ig_url="${BASE_URL}/webhooks/instagram"

printf 'Webhook registration targets:\n'
printf '  whatsapp_register_webhook  url=%s\n' "$wa_url"
printf '  instagram_register_webhook url=%s\n' "$ig_url"

if [[ "$DRY_RUN" -eq 1 ]]; then
  printf 'Dry-run complete: no MCP calls made and no credentials required.\n'
  exit 0
fi

if [[ -z "${STEPPE_MCP_TOKEN:-}" ]]; then
  printf 'STEPPE_MCP_TOKEN is required for live registration. Use --dry-run for local proof.\n' >&2
  exit 1
fi

if [[ ! -x "$PYTHON" ]]; then
  printf 'Python executable not found at %s\n' "$PYTHON" >&2
  printf 'Create the venv first, then retry.\n' >&2
  exit 1
fi

PYTHONPATH=orchestrator "$PYTHON" -m orchestrator.main \
  --register-webhooks "$BASE_URL" \
  --log-level "$LOG_LEVEL"
