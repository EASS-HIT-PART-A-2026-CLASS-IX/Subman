# 💰 SubMan Pro - Intelligent Subscription Management Suite

**Developer:** Maor Maimon  
**Course:** Engineering Advanced Software Systems (EASS)  
**Exercise:** EX1 (Backend), EX2 (Interface) & EX3 (Docker Orchestration, Async Worker & Architecture Security)

SubMan Pro is a production-grade, containerized subscription tracking and expense analytics suite. Architected as a decoupled microservices network running locally via Docker Compose, the system integrates a FastAPI backend web API, a highly polished Streamlit analytical interface, a persistent transactional PostgreSQL database, and an asynchronous background task worker managed via Redis.

---

## 📁 Project Structure
The project is organized as a unified, decoupled monorepo:
* `app/` - Core Backend API layer (FastAPI framework, SQLModel ORM, Security & JWT Auth).
* `frontend/` - SaaS Graphical Dashboard interface (Streamlit, Plotly visual engines).
* `scripts/` - Automated utilities including the async background engine (`refresh.py`) and infrastructure scripts.
* `tests/` - Comprehensive automated testing suite (Pytest framework covering logic and security states).

---

## 🏗️ System Architecture & Service Stack (EX3)

The stack maps 5 independent network resources communicating across an isolated internal Docker overlay bridge:
* **Frontend UI (Streamlit):** Runs on port `8501`. Features specialized custom styling hooks, unified responsive metric cards, real-time client-side subset sorting, and live category distribution tracking compiled via Pandas.
* **Backend API (FastAPI):** Runs on port `8000`. Powered by explicit `SQLModel` database entities, modern application `lifespan` initialization setups, and state-of-the-art `JWT (JSON Web Token)` security gates.
* **Database (PostgreSQL 15):** Runs on port `5432`. An enterprise transactional database engine maintaining fully isolated, persistent states across development cycles using named volume mappings.
* **Message Broker & Cache (Redis 7):** Operates internally on port `6379`. Functions as the decoupled high-speed message queue backbone and idempotency store driving background system processes.
* **Asynchronous Task Engine (Worker):** A background worker script tracking memory boundaries (`asyncio.Semaphore`), failure recoveries, and Redis processing layers to update subscription matrices concurrently.

---

## ✨ Core Features & Implementation Highlights

### 1. Robust Fault-Tolerant Startup (Db Wait-For-Ready)
To eliminate container initialization race conditions where the lightweight Python containers spin up faster than the heavier database clusters, the API implementation uses an **Exponential Retry Connection Loop** inside its lifespan block, safely delaying incoming requests until communication channels are secure.

### 2. High-Performance Server-Side DB Filtering
Instead of consuming massive system memory pools by reading raw rows sequentially into app contexts (`.all()`), the `/subscriptions/summary` analytical calculation tracks parse datasets directly within database query boundaries using targeted SQL `WHERE` evaluations.

### 3. Edge-Case Invariant Validation (The "2035 Constraint")
The calculation engines safely bypass data points locked into distant execution terms (e.g., Year 2035) from the current cycle metric indicators to avoid structural layout distortion. One-Time payments are intelligently evaluated within a rolling 30-day coverage range.

### 4. Non-Blocking Event Auditing Pipeline
Core transaction adjustments securely trigger decoupled processing context queues (`BackgroundTasks`), allowing data mutations to write to a localized persistent logging sequence (`audit.log`) without stalling active system pipelines.

### 5. Resilient Idempotent Background Task Worker (Session 09)
The dedicated worker tracking loop handles concurrent billing cycle refreshes safely using high-performance Redis constructs (`BRPOP`). It maintains rigorous **Idempotency Safeguards** via composite key locks (`subman:idempotency:refresh:sub:{id}:{date}`) ensuring each individual record is computed exactly once per day.

### 6. Role-Based Access Control and Token Expiry (Session 11)
Core database deletions require structural safety authorizations. The critical endpoint `DELETE /subscriptions/{name}` is protected behind custom OAuth2 authentication flows validating signature checks, token expiration parameters, and Admin role configurations.

---

## 🔐 Credentials (Hardcoded for Grading Rubric)

To allow seamless validation of the secure endpoints, the underlying engine loads two default roles:

| Username | Password | Role / Access Rights |
| :--- | :--- | :--- |
| `admin` | `subman123` | **Admin:** Full read access, dashboard control, and execution of data purging/deletions. |
| `viewer` | `viewonly` | **Viewer:** General read-only access. Blocked from data alterations (Deletions return HTTP 403). |

---

## 🚀 Getting Started (Docker Runbook)

### Prerequisites
Ensure **Docker Desktop** is active on your local device.

### Step 1: Allocate the Shared File Log
Ensure the persistent audit file template is generated locally before container binding to prevent Docker engine directory translation errors:

```powershell
# On Windows (PowerShell):
New-Item -ItemType File -Path audit.log -Force
```

### Step 2: Assemble and Deploy the Container Stack
Run the standard multi-container orchestration suite to provision, compile, network, and seed the entire microservice matrix:

```bash
docker compose up --build
```

### Step 3: Available Network Access Points
* **SaaS Web Dashboard:** http://localhost:8501
* **Self-Documenting API Explorer (Swagger UI):** http://localhost:8000/docs
* **Direct Database Entry:** `localhost:5432` (User: `subman` | Secret: `submanpass` | DB: `subman_db`)

---

## 🧪 Automated Test Suite Execution

The system delivers comprehensive engineering protection across database connections, business rules, and security frameworks using `pytest`. Testing routines map to a zero-overhead isolated in-memory model context (`sqlite:///:memory:` via `StaticPool`), keeping local database architectures safe.

### Run Tests from the Docker Environment
To ensure the code compiles natively inside the identical containerized ecosystem evaluated by CI and grading scripts, execute:

```bash
docker compose exec api python -m pytest tests/ -v
```

### Verified Test Suite Summary
* **`test_create_subscription`:** Validates insertion data mapping structures and accurate forecasting calculations.
* **`test_create_duplicate_subscription`:** Asserts core unique database entity protections by rejecting duplicate name strings with an `HTTP 400 Bad Request`.
* **`test_summary_burn_rate_and_filtering`:** Validates complex metric computations, relative datetime thresholds, exchange rates, and future state exclusions.
* **`test_delete_requires_token`:** Guarantees deletion targets are blocked without token inclusion, returning an explicit `HTTP 401 Unauthorized`.
* **`test_delete_expired_token_is_rejected`:** Confirms token lifespan checks block dated signatures.
* **`test_delete_viewer_role_is_forbidden`:** Confirms authorization levels successfully reject low-privilege `viewer` requests with an `HTTP 403 Forbidden`.
* **`test_delete_valid_admin_token_succeeds`:** Verifies successful resource purge sequences when a valid admin token signature is presented.

---

## 🤖 AI Assistance Declaration
In compliance with assignment requirements, Gemini (LLM) was leveraged as an interactive pairing partner across these milestones:
* **Architecture Design:** Assisting in migrating standalone database hooks to structured `lifespan` setup blocks, configuring database connections within separate thread boundaries (`StaticPool`), and implementing Redis queues.
* **Frontend Assembly:** Building injection rules, constructing structural Streamlit layout alignments, handling secure state tokens (`st.session_state`), and managing category groupings via Pandas.
* **Security & Worker Engineering:** Structuring the JWT signature evaluations, generating mock role credentials, and planning async execution paths featuring bounded concurrency throttles and idempotency claims.
* **Local Verification:** All logic paths, deployment manifests, security protocols, and testing structures were manually reviewed, compiled locally, and validated directly inside the runtime container layout.