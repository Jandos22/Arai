#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$script_dir/common.sh"

thread_id="ig-deshawn-001"
from="deshawn_office"
message='Hey, I want to set up a recurring dessert box for office Friday meetings, ~12 people, $200 budget per Friday. Do you do this?'
payload="$(jq -nc --arg threadId "$thread_id" --arg from "$from" --arg message "$message" \
  '{threadId:$threadId, from:$from, message:$message}')"

mcp_call instagram_inject_dm "$payload" >/dev/null
wait_for_persona_evidence "$thread_id" "DeShawn"
