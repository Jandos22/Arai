#!/usr/bin/env bash
# Scan committed history for real-looking secrets while allowing documented
# placeholders and test fixtures. Exits 0 when clean, 1 when a candidate leak
# remains after the allow-list.

set -euo pipefail

PATTERN='(sbc_team_[A-Za-z0-9_-]{8,}|Bearer[[:space:]]+[A-Za-z0-9._-]{20,}|[0-9]{8,12}:[A-Za-z0-9_-]{30,})'

ALLOW_PATTERN='(sbc_team_REPLACE_WITH_YOURS|sbc_team_xxxxxxxx|sbc_team_secret_blob_value_123|sbc_team_18bABCDEF1234567xyz|__paste_team_token_here_never_commit__)'

matches="$(
  git log -p --all --no-ext-diff \
    | grep -E "$PATTERN" \
    | grep -Ev "$ALLOW_PATTERN" \
    || true
)"

if [[ -n "$matches" ]]; then
  echo "LEAK: possible committed secret(s) found:" >&2
  echo "$matches" >&2
  exit 1
fi

echo "clean"
