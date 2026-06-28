# Runbook — Docker Compose (SubMan Pro)

Operational guide for building, running, health-checking, and testing the SubMan Pro multi-service stack.

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose v2)
- Ports **5432**, **8000**, and **8501** available on the host
- Optional: `curl` for manual health checks; Git Bash or WSL to run `scripts/demo.sh` on Windows

---

## 1. First-Time Setup

### 1.1 Initialize the audit log bind mount

Docker maps `./audit.log` into the API container. The path **must be a file**, not a directory.

**PowerShell (Windows):**

```powershell
New-Item -ItemType File -Path audit.log -Force
```

**Bash (Linux / macOS / Git Bash):**

```bash
touch audit.log
```

### 1.2 Build and start all services

From the repository root:

```bash
docker compose up --build
```

Add `-d` to run detached (background):

```bash
docker compose up --build -d
```

### 1.3 Expected startup order

1. `db` — PostgreSQL initializes data directory (first run may take ~10–20 s)
2. `api` — Waits for DB (retry loop in FastAPI lifespan), creates tables
3. `web` — Streamlit starts after `api` container is up (`depends_on`)

Watch logs for the API success message:

```
✅ Database connection successful! Tables are ready.
```

---

## 2. Access URLs

| Resource | URL |
|----------|-----|
| Streamlit dashboard | http://localhost:8501 |
| Swagger UI (API docs) | http://localhost:8000/docs |
| OpenAPI JSON | http://localhost:8000/openapi.json |
| PostgreSQL (host) | `localhost:5432` — user: `subman`, password: `submanpass`, db: `subman_db` |

---

## 3. Health Checks

There is no dedicated `/health` route yet. Use the checks below to confirm each layer is ready.

### 3.1 Database

```bash
docker compose exec -T db pg_isready -U subman -d subman_db
```

**Healthy output:** `accepting connections`

### 3.2 API

```bash
curl -sf http://localhost:8000/subscriptions
```

**Healthy:** HTTP 200 with JSON array (possibly empty `[]`).

Alternative — confirm OpenAPI is served:

```bash
curl -sf -o /dev/null -w "%{http_code}\n" http://localhost:8000/docs
```

**Healthy:** `200`

### 3.3 Streamlit frontend

```bash
curl -sf http://localhost:8501/_stcore/health
```

**Healthy:** HTTP 200

### 3.4 End-to-end smoke (single command)

```bash
curl -sf http://localhost:8000/subscriptions/summary
```

**Healthy:** JSON with keys `monthly_burn_rate_ils` and `active_subscriptions`.

---

## 4. Common Operations

### View logs

```bash
docker compose logs -f          # all services
docker compose logs -f api      # API only
docker compose logs -f web db   # frontend + database
```

### Restart a single service

```bash
docker compose restart api
```

### Stop the stack (keep data)

```bash
docker compose down
```

PostgreSQL data persists in the named volume `postgres_data`.

### Stop and remove volumes (⚠️ destroys DB data)

```bash
docker compose down -v
```

### Rebuild after code changes

```bash
docker compose up --build -d
```

---

## 5. Running Tests

Tests use an **in-memory SQLite** database via FastAPI dependency overrides. They do **not** require PostgreSQL or Docker to be running.

### Option A — Host environment (recommended for development)

If using `uv` (project includes `pyproject.toml`):

```bash
uv run pytest tests/ -v
```

Or with a local virtualenv where `pytest` is installed:

```bash
pytest tests/ -v
```

### Option B — Inside the API container

Install test dependencies in the container first (not included in `requirements.txt` by default):

```bash
docker compose exec api pip install pytest
docker compose exec api pytest tests/ -v
```

Or run a one-off container with pytest:

```bash
docker compose run --rm api pip install pytest && pytest tests/ -v
```

### Current test coverage

| Test | Validates |
|------|-----------|
| `test_create_subscription` | POST 201, auto `next_billing_date` |
| `test_create_duplicate_subscription` | Duplicate name → 400 |
| `test_delete_subscription` | DELETE 200, purge from ledger |

> **Note:** A dedicated `/subscriptions/summary` calculation test is planned in Step 2 of the EX3 gap analysis.

---

## 6. Automated Demo Script

A full spin-up + endpoint smoke test is available:

```bash
chmod +x scripts/demo.sh   # first time only (Linux/macOS/Git Bash)
./scripts/demo.sh
```

The script will:

1. Ensure `audit.log` exists
2. Build and start containers in detached mode
3. Poll health checks until services respond
4. Exercise CRUD + summary endpoints via `curl`
5. Print a pass/fail summary

---

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| API exits with "Database connection failed" | DB not ready in time | `docker compose restart api` or increase retries in `lifespan` |
| `audit.log` is a directory | File missing before first `up` | `docker compose down`, remove directory, `touch audit.log`, restart |
| Streamlit shows connection errors | API not running or wrong URL | Verify `BACKEND_URL=http://api:8000` on `web` service; check `docker compose logs api` |
| Port already in use | Another process on 8000/8501/5432 | Stop conflicting service or change port mappings in `compose.yml` |
| Stale data after schema change | Old Postgres volume | `docker compose down -v` (destroys data) and rebuild |

---

## 8. Service Reference (quick)

```yaml
services:
  db:   postgres:15          # port 5432, volume postgres_data
  api:  Dockerfile.api      # port 8000, DATABASE_URL → db
  web:  Dockerfile.web      # port 8501, BACKEND_URL → api
```

For architectural context, see [`docs/EX3-notes.md`](../EX3-notes.md).
