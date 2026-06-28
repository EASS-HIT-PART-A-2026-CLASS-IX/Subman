#!/usr/bin/env bash
# SubMan Pro — EX3 demo script
# Builds the Docker Compose stack, waits for health, and smoke-tests core API endpoints.
#
# Usage (from repo root):
#   chmod +x scripts/demo.sh
#   ./scripts/demo.sh
#
# Requirements: docker, docker compose, curl

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

API_BASE="http://localhost:8000"
WEB_BASE="http://localhost:8501"
DEMO_NAME="Demo Subscription $(date +%s)"
MAX_WAIT=120
INTERVAL=3

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass=0
fail=0

log()  { echo -e "${GREEN}[demo]${NC} $*"; }
warn() { echo -e "${YELLOW}[demo]${NC} $*"; }
err()  { echo -e "${RED}[demo]${NC} $*"; }

assert_http() {
  local label="$1"
  local expected="$2"
  local actual="$3"
  if [[ "$actual" == "$expected" ]]; then
    log "PASS — $label (HTTP $actual)"
    pass=$((pass + 1))
  else
    err "FAIL — $label (expected HTTP $expected, got HTTP $actual)"
    fail=$((fail + 1))
  fi
}

wait_for() {
  local label="$1"
  local cmd="$2"
  local elapsed=0
  log "Waiting for $label (max ${MAX_WAIT}s)..."
  until eval "$cmd"; do
    sleep "$INTERVAL"
    elapsed=$((elapsed + INTERVAL))
    if [[ $elapsed -ge $MAX_WAIT ]]; then
      err "Timeout waiting for $label"
      return 1
    fi
  done
  log "$label is ready (${elapsed}s)"
}

# ── Pre-flight ────────────────────────────────────────────────────────────────

if ! command -v docker >/dev/null 2>&1; then
  err "docker is not installed or not in PATH"
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  err "curl is not installed or not in PATH"
  exit 1
fi

if [[ ! -f audit.log ]]; then
  warn "audit.log missing — creating empty file for bind mount"
  touch audit.log
fi

# ── Spin up stack ─────────────────────────────────────────────────────────────

log "Building and starting Docker Compose stack..."
docker compose up --build -d

# ── Health checks ─────────────────────────────────────────────────────────────

wait_for "PostgreSQL" \
  "docker compose exec -T db pg_isready -U subman -d subman_db >/dev/null 2>&1"

wait_for "FastAPI" \
  "curl -sf '${API_BASE}/subscriptions' >/dev/null"

wait_for "Streamlit" \
  "curl -sf '${WEB_BASE}/_stcore/health' >/dev/null"

# ── Endpoint smoke tests ──────────────────────────────────────────────────────

log "Running API endpoint smoke tests..."

# GET /subscriptions (empty or populated)
code=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/subscriptions")
assert_http "GET /subscriptions" "200" "$code"

# POST /subscriptions
create_payload=$(cat <<EOF
{
  "name": "${DEMO_NAME}",
  "price": 49.90,
  "currency": "USD",
  "category": "software",
  "billing_cycle": "monthly",
  "status": "active",
  "purchase_date": "$(date +%Y-%m-%d)"
}
EOF
)

create_response=$(curl -s -w "\n%{http_code}" -X POST \
  -H "Content-Type: application/json" \
  -d "$create_payload" \
  "${API_BASE}/subscriptions")
create_body=$(echo "$create_response" | head -n -1)
create_code=$(echo "$create_response" | tail -n 1)
assert_http "POST /subscriptions" "201" "$create_code"

if echo "$create_body" | grep -q "\"next_billing_date\""; then
  log "PASS — POST response includes next_billing_date"
  pass=$((pass + 1))
else
  err "FAIL — POST response missing next_billing_date"
  fail=$((fail + 1))
fi

# GET /subscriptions/summary
summary_response=$(curl -s -w "\n%{http_code}" "${API_BASE}/subscriptions/summary")
summary_body=$(echo "$summary_response" | head -n -1)
summary_code=$(echo "$summary_response" | tail -n 1)
assert_http "GET /subscriptions/summary" "200" "$summary_code"

if echo "$summary_body" | grep -q "monthly_burn_rate_ils" && echo "$summary_body" | grep -q "active_subscriptions"; then
  log "PASS — summary payload contains expected keys"
  pass=$((pass + 1))
else
  err "FAIL — summary payload missing expected keys"
  fail=$((fail + 1))
fi

log "Summary response: $summary_body"

# DELETE /subscriptions/{name} (URL-encoded name)
encoded_name=$(python3 -c "import urllib.parse; print(urllib.parse.quote('${DEMO_NAME}'))" 2>/dev/null \
  || python -c "import urllib.parse; print(urllib.parse.quote('${DEMO_NAME}'))")
delete_code=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
  "${API_BASE}/subscriptions/${encoded_name}")
assert_http "DELETE /subscriptions/{name}" "200" "$delete_code"

# Verify deletion — second DELETE should 404
delete_again_code=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
  "${API_BASE}/subscriptions/${encoded_name}")
assert_http "DELETE again (expect 404)" "404" "$delete_again_code"

# ── Audit log (optional check) ────────────────────────────────────────────────

if [[ -f audit.log ]] && grep -qi "Created subscription" audit.log; then
  log "PASS — audit.log contains creation entry"
  pass=$((pass + 1))
else
  warn "SKIP — audit.log entry not found yet (background task may still be flushing)"
fi

# ── Summary ───────────────────────────────────────────────────────────────────

echo ""
echo "════════════════════════════════════════"
if [[ $fail -eq 0 ]]; then
  log "All checks passed ($pass assertions)"
  echo ""
  log "Dashboard:  ${WEB_BASE}"
  log "API docs:   ${API_BASE}/docs"
  echo ""
  log "Stack is running in detached mode. Stop with: docker compose down"
  exit 0
else
  err "$fail check(s) failed, $pass passed"
  err "Inspect logs: docker compose logs api web db"
  exit 1
fi
