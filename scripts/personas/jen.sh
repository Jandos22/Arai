#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$script_dir/common.sh"

from="+1832555-JENJN"
message="Hi! Saw your cloud cake on instagram — can I get a whole one for tomorrow afternoon? My daughter's birthday and I forgot to order earlier 😅"
payload="$(jq -nc --arg from "$from" --arg message "$message" '{from:$from, message:$message}')"

mcp_call whatsapp_inject_inbound "$payload" >/dev/null
wait_for_persona_evidence "$from" "Jen"
