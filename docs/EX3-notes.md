# EX3 — Architectural Notes (SubMan Pro)

**Author:** Maor Maimon  
**Course:** Engineering Advanced Software Systems (EASS)  
**Exercise:** EX3 — Docker Orchestration, Persistence & Production Patterns

This document records the key architectural decisions made while evolving SubMan Pro from a single-process prototype (EX1/EX2) into a multi-service, containerized stack suitable for local production-style deployment.

---

## 1. System Overview

SubMan Pro is a subscription management and expense analytics suite composed of three cooperating services:

| Service | Technology | Host port | Responsibility |
|---------|------------|-----------|----------------|
| `web` | Streamlit | 8501 | Dashboard UI, charts, CRUD forms |
| `api` | FastAPI + SQLModel | 8000 | REST API, business logic, audit logging |
| `db` | PostgreSQL 15 | 5432 | Durable relational storage |

All services are defined in `docker-compose.yml` and share an isolated Docker bridge network. The host machine reaches services via published ports; inter-container traffic uses Docker DNS service names (`api`, `db`).

```
┌─────────────┐     HTTP (8501)      ┌──────────────┐
│   Browser   │ ───────────────────► │  web (UI)    │
└─────────────┘                      └──────┬───────┘
                                            │ HTTP
                                            │ http://api:8000
                                            ▼
                                     ┌──────────────┐     SQL      ┌─────────────┐
                                     │  api (API)   │ ───────────► │ db (Postgres)│
                                     └──────┬───────┘              └─────────────┘
                                            │
                                            ▼
                                     audit.log (bind mount)
```

---

## 2. PostgreSQL over SQLite

### Decision

**Production / Docker path:** PostgreSQL via `DATABASE_URL=postgresql://subman:submanpass@db:5432/subman_db`  
**Local dev fallback:** SQLite via `DATABASE_URL` default `sqlite:///subman.db`

### Rationale

| Concern | SQLite (file) | PostgreSQL (service) |
|---------|---------------|----------------------|
| Multi-container access | Poor — file locking, single-writer | Native — TCP connection pool |
| Durability across restarts | File on host; fragile in containers | Named volume `postgres_data` |
| Concurrent requests | Limited write concurrency | ACID transactions under load |
| EX3 grading criteria | Acceptable for unit tests only | Required for orchestrated stack |

SQLite remains valuable **only** for:

- Fast local development without Docker
- Isolated `pytest` runs (`sqlite:///:memory:`) that must not touch production data

The API reads the connection string from the environment (`os.getenv("DATABASE_URL", ...)`) and applies SQLite-specific `connect_args` only when `"sqlite"` appears in the URL:

```python
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
```

### Startup race condition

PostgreSQL takes longer to boot than the API container. The FastAPI `lifespan` handler implements an **exponential retry loop** (5 attempts, 3-second pause) before calling `SQLModel.metadata.create_all(engine)`. This prevents the API from crashing when it starts before the database accepts connections.

---

## 3. Service Communication

### Frontend → API

The Streamlit container cannot call `http://127.0.0.1:8000` for backend requests — inside the `web` container, `localhost` refers to the Streamlit process itself, not the API.

**Current implementation:** The Streamlit app uses `API_URL = "http://api:8000"`, which resolves correctly inside the `web` container via Docker DNS.

**Compose configuration (prepared for host-aware fallback):** The `web` service also injects `BACKEND_URL=http://api:8000`. A future improvement is:

```python
API_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
```

When developing on the host (without Docker), change the fallback to `http://127.0.0.1:8000` or set `BACKEND_URL` in the environment.

### API → Database

The API connects to PostgreSQL using the service name `db` as the hostname (Docker Compose DNS). Credentials and database name are provisioned via `POSTGRES_*` environment variables on the `db` service and mirrored in the API's `DATABASE_URL`.

### Audit trail (API → filesystem)

Mutation endpoints (`POST`, `DELETE`) enqueue `log_audit_trail` via FastAPI `BackgroundTasks`. Entries append to `audit.log`. In Docker, a **bind mount** maps `./audit.log` on the host to `/app/audit.log` in the API container so logs survive container restarts and are inspectable from the host.

> **Important:** Create `audit.log` as an empty file on the host **before** the first `docker compose up`. If the file does not exist, Docker may create a directory instead of a file at that path.

---

## 4. Data Layer (SQLModel)

- **Single table model:** `Subscription` (`app/models.py`) with `table=True`
- **ORM + validation:** SQLModel merges Pydantic validation with SQLAlchemy persistence
- **Session injection:** Routes depend on `get_session()` — tests override this dependency with an in-memory SQLite engine

Key invariants enforced at the API layer:

- Case-insensitive duplicate name rejection on `POST`
- Server-side calculation of `next_billing_date` (client does not supply it)
- Summary endpoint filters future-dated subscriptions and applies a 30-day window for one-time purchases

---

## 5. Configuration Summary

| Variable | Set by | Purpose |
|----------|--------|---------|
| `DATABASE_URL` | `api` service in compose | PostgreSQL connection string |
| `BACKEND_URL` | `web` service in compose | Internal API base URL for Streamlit |
| `POSTGRES_USER/PASSWORD/DB` | `db` service | Database bootstrap |

---

## 6. Planned EX3 Extensions (upcoming steps)

The following items are tracked in the gap analysis and will be added incrementally:

| Step | Item | Status |
|------|------|--------|
| 1 | Documentation & `scripts/demo.sh` | ✅ This document + runbook |
| 2 | Summary endpoint test | Pending |
| 3 | Redis + async worker (`scripts/refresh.py`) | Pending |
| 4 | JWT auth + protected routes | Pending |

Each step is implemented and verified independently to avoid regressions in the working CRUD stack.

---

## 7. References

- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)
- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [Docker Compose Networking](https://docs.docker.com/compose/networking/)
- Project runbook: [`docs/runbooks/compose.md`](runbooks/compose.md)
