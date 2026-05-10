#!/usr/bin/env bash
# Shared env loader for worktrees.
#
# Precedence:
#   1. ARAI_ENV_FILE, if set
#   2. <repo>/.env.local
#   3. ~/.config/arai/env.local
#
# Usage:
#   source scripts/load_env.sh
#   arai_load_env "$repo_root"

arai_load_env() {
  local repo_root="${1:?repo root required}"
  local candidates=()

  if [[ -n "${ARAI_ENV_FILE:-}" ]]; then
    candidates+=("$ARAI_ENV_FILE")
  fi
  candidates+=("$repo_root/.env.local")
  candidates+=("$HOME/.config/arai/env.local")

  local env_file
  for env_file in "${candidates[@]}"; do
    if [[ -f "$env_file" ]]; then
      set -a
      # shellcheck disable=SC1090
      source "$env_file"
      set +a
      export ARAI_ENV_FILE_LOADED="$env_file"
      return 0
    fi
  done

  return 1
}
