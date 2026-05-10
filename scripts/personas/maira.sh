#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$script_dir/common.sh"

from="+1281555-MAIRA"
message='Salam! Need a medovik for Nauryz on Saturday, 12 people. My elener apa is allergic to walnuts — can you guarantee no nuts at all?'
payload="$(jq -nc --arg from "$from" --arg message "$message" '{from:$from, message:$message}')"

mcp_call whatsapp_inject_inbound "$payload" >/dev/null
wait_for_persona_evidence "$from" "Maira"
