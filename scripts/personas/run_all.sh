#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
cd "$repo_root"

declare -a evidence_files=()

for persona in maira jen deshawn; do
  echo "persona:${persona}: injecting"
  evidence_file="$("$script_dir/${persona}.sh")"
  evidence_files+=("$evidence_file")
  echo "persona:${persona}: evidence=${evidence_file}"
done

latest="$(ls -t evidence/orchestrator-*.jsonl 2>/dev/null | head -1)"
if [[ -z "$latest" ]]; then
  echo "No orchestrator evidence found after persona run" >&2
  exit 1
fi

out="evidence/personas-$(date -u +%Y%m%dT%H%M%SZ).jsonl"
{
  echo "# Persona evidence files: ${evidence_files[*]}"
  tail -n 240 "$latest"
} > "$out"

echo "personas_transcript=$out"
