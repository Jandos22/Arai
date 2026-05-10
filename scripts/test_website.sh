#!/usr/bin/env bash
# test_website.sh — build the Next.js website and verify every agent-readable
# endpoint returns the expected shape. No MCP token required; uses the
# fixture catalog as a deterministic baseline.
#
# Usage:
#   bash scripts/test_website.sh
#
# Exits non-zero on any failure. Designed to be safe to run as a CI step.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root/website"

PORT="${PORT:-3737}"
BASE="http://localhost:${PORT}"

red()    { printf '\033[31m%s\033[0m\n' "$*"; }
green()  { printf '\033[32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[33m%s\033[0m\n' "$*"; }

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

if [[ ! -d node_modules ]]; then
  yellow "Installing website deps (npm install)…"
  npm install --no-fund --no-audit --silent
fi

yellow "Building website…"
npm run build > /tmp/arai-website-build.log 2>&1 || {
  red "BUILD FAILED — see /tmp/arai-website-build.log"
  tail -40 /tmp/arai-website-build.log
  exit 1
}
green "Build OK"

yellow "Starting server on :$PORT (background)…"
npm start -- -p "$PORT" > /tmp/arai-website-run.log 2>&1 &
SERVER_PID=$!

# Wait for ready, up to 20s.
for _ in {1..40}; do
  if curl -sf "${BASE}/agent.json" > /dev/null 2>&1; then
    break
  fi
  sleep 0.5
done
if ! curl -sf "${BASE}/agent.json" > /dev/null 2>&1; then
  red "Server didn't become ready"
  tail -40 /tmp/arai-website-run.log
  exit 1
fi
green "Server ready"

failures=0

# 1. /agent.json
agent=$(curl -sS "${BASE}/agent.json")
echo "$agent" | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["name"] == "HappyCake US", "agent.json: wrong name"
assert "capabilities" in d and len(d["capabilities"]) >= 3
assert d["endpoints"]["catalog"] == "/api/catalog"
assert d["endpoints"]["policies"] == "/api/policies"
print("agent.json OK")
' || { red "/agent.json FAILED"; failures=$((failures+1)); }

# 2. /api/catalog
catalog=$(curl -sS "${BASE}/api/catalog")
echo "$catalog" | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert "items" in d
assert d["source"] in ("fixture", "mcp-snapshot")
assert len(d["items"]) >= 1
for item in d["items"]:
    for k in ("id", "slug", "name", "variations"):
        assert k in item, f"item missing {k}"
print("api/catalog OK ({} items, source={})".format(len(d["items"]), d["source"]))
' || { red "/api/catalog FAILED"; failures=$((failures+1)); }

# 3. /api/policies
policies=$(curl -sS "${BASE}/api/policies")
echo "$policies" | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["business"]["name"] == "HappyCake US"
assert "ordering" in d and "channels" in d["ordering"]
assert "allergens" in d
print("api/policies OK")
' || { red "/api/policies FAILED"; failures=$((failures+1)); }

# 4. JSON-LD on a product page
slug=$(echo "$catalog" | python3 -c '
import json, sys
d = json.load(sys.stdin)
print(d["items"][0]["slug"])
')
prod=$(curl -sS "${BASE}/p/${slug}")
if echo "$prod" | grep -q 'application/ld+json'; then
  green "JSON-LD on /p/${slug} OK"
else
  red "JSON-LD missing on /p/${slug}"
  failures=$((failures+1))
fi

# 5. Website order-intent API creates source=website handoff metadata
order_payload=$(python3 - <<PY
import json
print(json.dumps({
  "productSlug": "$slug",
  "quantity": 1,
  "customerName": "Website Smoke",
  "contact": "+12815550000",
  "pickupDate": "2026-05-10",
  "pickupTime": "12:00",
  "notes": "website smoke order",
  "attribution": {
    "landingPath": "/office-boxes",
    "campaign": "office-boxes",
    "campaignId": "mkt_smoke_office_boxes",
    "channel": "google_local",
    "utm_source": "google_local",
    "utm_medium": "paid_local",
    "utm_campaign": "office_boxes_sugar_land",
    "utm_content": "smoke"
  }
}))
PY
)
order_intent=$(curl -sS -X POST "${BASE}/api/order-intent" -H 'Content-Type: application/json' --data "$order_payload")
echo "$order_intent" | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["ok"] is True
intent = d["intent"]
assert intent["source"] == "website"
assert intent["attribution"]["landingPath"] == "/office-boxes"
assert intent["attribution"]["utm"]["source"] == "google_local"
assert intent["attribution"]["utm"]["campaign"] == "office_boxes_sugar_land"
assert intent["handoff"]["campaignLead"]["routeTo"] == "website"
assert "landingPath=/office-boxes" in intent["handoff"]["campaignLead"]["evidence"]
assert intent["handoff"]["cashier"]["tool"] == "square_create_order"
assert intent["handoff"]["kitchen"]["tool"] == "kitchen_create_ticket"
print("api/order-intent OK")
' || { red "/api/order-intent FAILED"; failures=$((failures+1)); }

# 5b. Campaign routing covers website, WhatsApp, Instagram, and owner approval
python3 - "$BASE" "$slug" <<'PY' || { red "campaign routing variants FAILED"; failures=$((failures+1)); }
import json
import sys
import urllib.request

base, slug = sys.argv[1], sys.argv[2]
cases = [
    ("google_local", 1, "website smoke route", "website"),
    ("whatsapp", 1, "whatsapp smoke route", "whatsapp"),
    ("instagram", 1, "instagram smoke route", "instagram"),
    ("google_local", 3, "owner approval smoke route", "owner_approval"),
]

for source, quantity, notes, expected_route in cases:
    payload = {
        "productSlug": slug,
        "quantity": quantity,
        "customerName": "Campaign Smoke",
        "contact": "+12815550000",
        "notes": notes,
        "attribution": {
            "landingPath": "/office-boxes",
            "campaign": "office-boxes",
            "channel": source,
            "utm_source": source,
            "utm_medium": "paid_local",
            "utm_campaign": "office_boxes_sugar_land",
        },
    }
    req = urllib.request.Request(
        f"{base}/api/order-intent",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        data = json.load(response)
    intent = data["intent"]
    route = intent["handoff"]["campaignLead"]["routeTo"]
    assert route == expected_route, f"{source}/{quantity}: expected {expected_route}, got {route}"
    evidence = intent["handoff"]["campaignLead"]["evidence"]
    assert f"routeTo={expected_route}" in evidence
    assert "campaign=office-boxes" in evidence

print("campaign routing variants OK")
PY

# 6. On-site assistant API covers evaluator-driving paths
assistant=$(curl -sS -X POST "${BASE}/api/assistant" -H 'Content-Type: application/json' --data '{"message":"I need a custom birthday cake tomorrow afternoon"}')
echo "$assistant" | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["ok"] is True
assert d["intent"] == "custom_order"
assert d["escalation"]["required"] is True
print("api/assistant OK")
' || { red "/api/assistant FAILED"; failures=$((failures+1)); }

# 7. Static pages render (not 404)
for path in "/" "/menu" "/office-boxes" "/about" "/policies" "/order" "/assistant"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "${BASE}${path}")
  if [[ "$code" != "200" ]]; then
    red "GET ${path} -> ${code}"
    failures=$((failures+1))
  fi
done
green "All static pages OK"

# 8. Campaign landing page carries attribution into the order path
office_boxes=$(curl -sS "${BASE}/office-boxes")
if echo "$office_boxes" | grep -q 'utm_campaign=office_boxes_sugar_land' && echo "$office_boxes" | grep -q 'landingPath=%2Foffice-boxes'; then
  green "Campaign landing attribution on /office-boxes OK"
else
  red "Campaign attribution missing on /office-boxes"
  failures=$((failures+1))
fi

if (( failures > 0 )); then
  red "==== FAIL: ${failures} check(s) failed ===="
  exit 1
fi

green "==== PASS — website agent-readable surface verified ===="
