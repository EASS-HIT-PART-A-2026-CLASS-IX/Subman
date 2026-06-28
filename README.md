# 💳 SubMan Pro — Intelligent Subscription Management Suite

**Developer:** Maor Maimon  
**Course:** Engineering Advanced Software Systems (EASS) — Class IX, 2026  
**Exercises:** EX1 (Backend) · EX2 (Interface) · EX3 (Full-Stack Microservices)

SubMan Pro is a production-grade subscription tracking and expense analytics suite. It runs as a fully containerized multi-service stack via Docker Compose — FastAPI backend, Streamlit dashboard, PostgreSQL persistence, Redis async worker, and JWT-secured endpoints.

---

## 📁 Project Structure

```
subman-project/
├── app/
│   ├── main.py          # FastAPI routes, lifespan, billing logic
│   ├── models.py        # SQLModel Subscription table
│   ├── auth.py          # JWT helpers, bcrypt hashing, role guards
│   └── seedscript.py    # Database seed script (+5 bonus)
├── frontend/
│   └── app.py           # Streamlit dark-theme dashboard
├── scripts/
│   ├── refresh.py       # Async Redis worker (Session 09)
│   └── demo.sh          # End-to-end grader demo script
├── tests/
│   ├── test_main.py     # CRUD + burn-rate tests
│   └── test_auth.py     # JWT security tests (4 scenarios)
├── docs/
│   ├── EX3-notes.md     # Architecture decisions & Redis trace
│   └── runbooks/
│       └── compose.md   # Operational runbook for graders
├── docker-compose.yml
├── Dockerfile.api
├── Dockerfile.web
├── Dockerfile.worker
└── requirements.txt
```

---

## 🏗️ Service Topology

| Service | Technology | Port | Purpose |
|---------|-----------|------|---------|
| `api` | FastAPI + SQLModel + Uvicorn | 8000 | Core CRUD backend + JWT auth |
| `db` | PostgreSQL 15 | 5432 | Persistent relational storage |
| `redis` | Redis 7 Alpine | 6379 | Job queue + idempotency store |
| `worker` | Python asyncio | — | Async billing refresh worker |
| `web` | Streamlit | 8501 | Dark-themed SaaS dashboard UI |

---

## 🚀 Quick Start

### Prerequisites

- Docker Desktop running on your machine

### Step 1 — Create the audit log file

Docker maps mounted files as directories if the file doesn't exist first. Create it manually:

```powershell
# Windows PowerShell
New-Item -ItemType File -Path audit.log -Force
```

```bash
# macOS / Linux
touch audit.log
```

### Step 2 — Build and launch all services

```bash
docker compose up --build -d
```

This downloads images, builds the api / web / worker containers, starts PostgreSQL and Redis, and wires all services on an isolated Docker network.

> 💡 **Seed the database (bonus):** By default the database starts empty. To populate it with realistic sample subscriptions run the seed command listed in the Docker Operations section below.

### Step 3 — Open the applications

| Application | URL | Notes |
|-------------|-----|-------|
| Streamlit Dashboard | http://localhost:8501 | Main user-facing UI |
| FastAPI Swagger UI | http://localhost:8000/docs | Interactive API explorer + JWT auth |
| PostgreSQL | localhost:5432 | User: `subman` · Pass: `submanpass` · DB: `subman_db` |

---

## 🧪 Running the Tests

All 8 tests run against an isolated in-memory SQLite database — zero side-effects on production data.

```bash
docker compose exec api python -m pytest tests/ -v
```

### Expected output

```
collected 8 items

tests/test_auth.py::test_delete_requires_token               PASSED  [ 12%]
tests/test_auth.py::test_delete_expired_token_is_rejected    PASSED  [ 25%]
tests/test_auth.py::test_delete_viewer_role_is_forbidden     PASSED  [ 37%]
tests/test_auth.py::test_delete_valid_admin_token_succeeds   PASSED  [ 50%]
tests/test_main.py::test_create_subscription                 PASSED  [ 62%]
tests/test_main.py::test_create_duplicate_subscription       PASSED  [ 75%]
tests/test_main.py::test_delete_subscription                 PASSED  [ 87%]
tests/test_main.py::test_summary_burn_rate_and_filtering     PASSED  [100%]

=========================== 8 passed in 1.43s ===========================
```

### Test coverage breakdown

| Test | File | What it validates |
|------|------|-------------------|
| `test_create_subscription` | test_main.py | Happy-path insert + `next_billing_date` calculation |
| `test_create_duplicate_subscription` | test_main.py | HTTP 400 on duplicate name |
| `test_delete_subscription` | test_main.py | Admin-token DELETE returns 200 |
| `test_summary_burn_rate_and_filtering` | test_main.py | Burn rate math, currency conversion, status filtering |
| `test_delete_requires_token` | test_auth.py | No token → HTTP 401 |
| `test_delete_expired_token_is_rejected` | test_auth.py | Expired JWT → HTTP 401 |
| `test_delete_viewer_role_is_forbidden` | test_auth.py | Viewer role on admin route → HTTP 403 |
| `test_delete_valid_admin_token_succeeds` | test_auth.py | Valid admin JWT → HTTP 200 |

---

## 🔐 Authentication

`DELETE /subscriptions/{name}` is protected and requires an admin JWT token.

### Credentials

| Username | Password | Role | Can Delete? |
|----------|----------|------|-------------|
| `admin` | `subman123` | admin | ✅ Yes |
| `viewer` | `viewonly` | viewer | ❌ No — returns HTTP 403 |

### Get a token

```bash
curl -X POST http://localhost:8000/auth/token \
  -d "username=admin&password=subman123" \
  -H "Content-Type: application/x-www-form-urlencoded"
```

### Use the token

```bash
curl -X DELETE "http://localhost:8000/subscriptions/Netflix" \
  -H "Authorization: Bearer <your_token_here>"
```

> **Tip:** Open http://localhost:8000/docs, click the green **Authorize** button, and enter the credentials — all protected endpoints then work directly in the browser.

---

## ✨ Features

### Core API

- Full CRUD for subscriptions (`GET`, `POST`, `DELETE`)
- Multi-currency support — ILS, USD, EUR with FX normalization
- Automatic `next_billing_date` — always returns a future date regardless of purchase date
- Monthly burn rate with per-cycle normalization (daily × 30, weekly × 4.33, yearly ÷ 12)
- One-time purchase clamping — only counted within the 30-day rolling window
- Future-dated subscriptions stored but excluded from monthly metrics (the "2035 constraint")
- Background audit trail — every CREATE and DELETE appended to `audit.log` without blocking HTTP

### Streamlit Dashboard

- Dark high-tech SaaS theme (Inter + JetBrains Mono fonts)
- Three metric cards: Monthly Burn Rate, Active Subscriptions, Budget Utilization with progress bar
- Billing alert banner — shows subscriptions due within 3 days
- Category filter + 4 sort options powered by Pandas
- Color-coded category pills (purple = entertainment, teal = health, blue = software, amber = sport)
- Excel export — one-click download of the full subscription ledger
- Spend by Category donut chart + Spend by Currency bar chart (Plotly)
- 7-day billing timeline with color-coded status dots in the Analytics tab
- Admin login panel in sidebar — fetches JWT and stores in `st.session_state`

---

## 🔄 Async Worker (Session 09)

`scripts/refresh.py` is a standalone async worker that:

- Connects to both PostgreSQL and Redis on startup with retries
- Pushes refresh jobs onto `subman:refresh:queue` via `RPUSH`
- Consumes jobs with `BRPOP` using `asyncio.Semaphore(MAX_CONCURRENCY)` for bounded concurrency
- Idempotency key: `subman:idempotency:refresh:sub:{id}:{YYYY-MM-DD}` — one refresh per subscription per day
- Retries failed jobs up to 3 times with exponential backoff (1s → 2s → 4s)
- Re-enqueues all eligible subscriptions every 60 seconds

```bash
# Watch worker logs
docker compose logs -f worker
```

---

## 🔒 Security (Session 11)

- Passwords hashed with **bcrypt** via `passlib` — never stored in plaintext
- **HS256 JWT tokens** signed with a secret key, 30-minute expiry
- `DELETE /subscriptions/{name}` requires `role=admin` — viewer tokens receive HTTP 403
- Token rotation: re-call `POST /auth/token` with valid credentials
- 4 security tests covering: no token, expired token, wrong role, valid admin

---

## 🐳 Docker Operations

```bash
# Build and start all services
docker compose up --build -d

# Stop (keep data volumes)
docker compose down

# Stop and wipe database (fresh start)
docker compose down -v

# Check all container statuses
docker compose ps -a

# Run the full test suite
docker compose exec api python -m pytest tests/ -v

# Populate database with realistic seed data (+5 bonus)
docker compose exec api python -m app.seedscript

# View the audit log
docker compose exec api cat audit.log

# Run the end-to-end demo script
chmod +x scripts/demo.sh && ./scripts/demo.sh
```

### Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `api` exited (1) | Import error or missing package | `docker compose logs api` to read traceback |
| `worker` restarting | API not yet healthy | Fix api first — worker imports from `app.main` |
| pip timeout during build | Slow network | Re-run `docker compose up --build -d` |
| `tests/` not found in container | `COPY tests/` missing from Dockerfile.api | Add `COPY tests/ ./tests/` and rebuild |
| 401 on DELETE | No token passed | Login at `/docs` or pass `Authorization: Bearer <token>` |

---

## 📋 EX3 Rubric Checklist

| Requirement | Status | Evidence |
|-------------|--------|----------|
| 3+ cooperating services | ✅ | api + db + redis + worker + web |
| `compose.yaml` + runbook | ✅ | `docker-compose.yml` + `docs/runbooks/compose.md` |
| `scripts/refresh.py` async worker | ✅ | Redis queue, semaphore, idempotency, backoff |
| JWT-protected route + role checks | ✅ | `app/auth.py` + `DELETE /subscriptions/{name}` |
| Hashed credentials | ✅ | bcrypt via passlib |
| Tests for expired/missing token | ✅ | `tests/test_auth.py` — 4 scenarios |
| Thoughtful enhancement | ✅ | Excel export, filters, charts, billing timeline |
| Automated tests covering enhancement | ✅ | `test_summary_burn_rate_and_filtering` |
| `scripts/demo.sh` | ✅ | Smoke-tests 5 endpoints, prints pass/fail |
| `docs/EX3-notes.md` | ✅ | Architecture decisions + Redis trace |
| `docs/runbooks/compose.md` | ✅ | Full operational runbook |
| Seed script | ✅ (+5) | `app/seedscript.py` — run via `python -m app.seedscript` |

---

## 🤖 AI Assistance Declaration

As required by submission guidelines, the following AI tools were used as pairing partners:

- **Claude (Anthropic)** — primary assistant throughout EX1, EX2, and EX3
- **Cursor (free tier)** — in-editor assistance for specific implementation steps

**How AI was used:**

- **Architecture:** `lifespan` migration, PostgreSQL-over-SQLite decision, retry loop design
- **Backend:** billing date logic, 2035 constraint filter, Redis idempotency worker
- **Security:** JWT auth flow, bcrypt integration, role-based access control, security test design
- **Frontend:** Streamlit CSS overrides, dark theme token system, metric cards, admin login panel
- **DevOps:** Dockerfile structure, Compose health checks, `demo.sh` smoke test script

**Verification:** All AI-generated code was reviewed line by line, manually tested via Swagger UI, and validated by running the full test suite (`8/8 passing`) inside the Docker container.