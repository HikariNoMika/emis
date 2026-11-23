# Environmental Monitoring Information System (EMIS)

A production-oriented, modular-monolith application for managing data from multiple
environmental monitoring stations. Built with **FastAPI** (Python) and **React + Vite**
(plain JavaScript / JSX).

> **Status: Backend migrated to FastAPI; Phases 1–6 and 8 code complete; Phase 7 scaffolded (blocked on official API docs).**
> All functional modules are implemented. Verification is still pending because
> the build environment had no Python or Node runtime — see "Important notes".
> The system was built one phase at a time, with tests written for each module.

---

## 1. Why these architectural choices

| Decision | Reason |
|---|---|
| Modular monolith, not microservices | One database, one deployable backend. Simpler to learn, debug and operate. Boundaries are kept clean with routes → services → repositories → models so modules can later be split if ever needed. |
| FastAPI application factory (`create_app`) | Allows different configs for development, testing and production, and makes test setup trivial. |
| Business logic in `services/` | Routes stay thin (parse request → call service → return JSON). This keeps rules testable without an HTTP server. |
| Pydantic schemas | Validates and normalizes incoming JSON before it reaches a service. Invalid requests get consistent 400 responses. |
| TimescaleDB hypertable for `measurements` | Measurements are time-series. Hybrid row/column compression and time-based indexing make trend queries fast. |
| JSONB for raw imported payloads | An uploaded Excel/CSV row can have unexpected extra columns. Storing the untouched row as JSONB means we never lose original data. |
| `original_value` **and** `normalized_value` | We preserve exactly what the station reported and separately store any converted value. Source data is never silently modified. |
| JWT with short-lived access tokens + longer refresh tokens | Standard stateless auth. Logout uses a blocklist (see note in `backend/app/utils/security.py`). |
| React Query (TanStack Query) | Handles caching, loading/error states, and background refetching so dashboard values are always fetched from the API. |

**Note on data honesty:** no dashboard number is hard-coded. Every card and chart
calls a REST endpoint that reads the database.

---

## 2. Technology stack

**Frontend:** React 18, JavaScript (JSX — no TypeScript), Vite, React Router,
Tailwind CSS, Apache ECharts (`echarts-for-react`), Leaflet (`react-leaflet`),
Axios, TanStack Query, React Hook Form, Zod.

**Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic,
PyJWT, Pydantic, CORS middleware, Pandas, OpenPyXL,
NumPy, Celery, Redis, ReportLab.

**Database:** PostgreSQL 16 with the TimescaleDB extension.

**Deployment:** Docker, Docker Compose, Nginx.

---

## 3. Project structure

```
emis/
├─ backend/
│  ├─ app/
│  │  ├─ __init__.py          # application factory
│  │  ├─ config.py            # environment-based settings
│  │  ├─ extensions.py        # shared extension instances
│  │  ├─ models/              # SQLAlchemy tables
│  │  ├─ schemas/             # Pydantic validation
│  │  ├─ routes/              # HTTP endpoints (blueprints)
│  │  ├─ services/            # business logic
│  │  ├─ repositories/        # database queries
│  │  ├─ processors/          # file parsing / validation (later phases)
│  │  ├─ integrations/        # excel, csv, official API connectors (later)
│  │  ├─ tasks/               # Celery jobs (later)
│  │  └─ utils/               # responses, security, time helpers
│  ├─ migrations/             # Alembic migrations
│  ├─ tests/
│  ├─ requirements.txt
│  ├─ .env.example
│  ├─ run.py                  # development server entrypoint
│  ├─ seed.py                 # creates the first administrator + reference data
│  └─ Dockerfile
├─ frontend/
│  ├─ src/
│  │  ├─ components/          # reusable UI + layout
│  │  ├─ context/             # AuthContext
│  │  ├─ pages/               # route pages
│  │  ├─ services/            # axios client + API calls
│  │  ├─ App.jsx
│  │  └─ main.jsx
│  ├─ public/
│  ├─ package.json
│  ├─ vite.config.js
│  ├─ tailwind.config.js
│  └─ Dockerfile
├─ docker/
│  └─ nginx.conf
├─ docker-compose.yml
└─ README.md
```

---

## 4. Database design (summary)

| # | Table | Purpose |
|---|---|---|
| 1 | `users` | Administrator accounts (hashed passwords only) |
| 2 | `login_history` | Login/logout audit trail (extra table for requirement 4) |
| 3 | `stations` | Monitoring stations, GPS coordinates, status, device serial |
| 4 | `sensors` | Equipment installed at a station (port, model, serial, calibration dates) |
| 5 | `measurement_types` | e.g. `air_temperature`, with units and valid ranges |
| 6 | `sensor_measurement_types` | Flexible link: one sensor → many measurement types |
| 7 | `data_sources` | `excel`, `csv`, future `official_api` |
| 8 | `import_batches` | One uploaded file = one batch, with mapping + metadata JSONB |
| 9 | `raw_import_records` | Untouched source rows as JSONB (never deleted) |
| 10 | `measurements` | Time-series hypertable, original + normalized values |
| 11 | `data_quality_flags` | VALID / SUSPECT / INVALID / MISSING / UNVERIFIED findings |
| 12 | `station_status` | Data freshness, battery and connectivity snapshots |
| 13 | `alerts` | Active/acknowledged/resolved alerts with dedupe key |
| 14 | `alert_history` | Status-change history for each alert |
| 15 | `maintenance_records` | Maintenance and calibration records |
| 16 | `audit_logs` | Important administrative actions with before/after JSONB |
| 17 | `system_settings` | Configurable thresholds and rules as JSONB |
| 18 | `reports` | Generated PDF/XLSX report history |
| 19 | `sync_logs` | Reserved for the future official API synchronizer |

Key rules encoded in the models:
- Every foreign key is enforced.
- `measurements` unique index includes `observation_time` (TimescaleDB requirement).
- Stations are **archived** (`is_archived = true`), never hard-deleted once they have data.
- Timestamps are timezone-aware (`DateTime(timezone=True)`).

A detailed diagram/notes will be expanded as later phases add constraints.

---

## 5. Getting started (local development)

### 5.1 Prerequisites
- Python 3.11+ and Node.js 20+
- PostgreSQL 16 + TimescaleDB **or** Docker / Docker Compose (recommended)

### 5.2 First-time setup (Docker)

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python seed.py
```

Then open <http://localhost:5173>. Default seed login is printed by `seed.py`
(you are forced to change the password on first use in later phases — for Phase 1
use the credentials from your `.env`).

### 5.3 Running without Docker

```bash
# Backend
cd backend
python -m venv venv
# Windows: venv\Scripts\activate        macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
# create an empty PostgreSQL database named "emis" first
alembic upgrade head
python seed.py
python run.py            # http://localhost:5000

# Frontend (second terminal)
cd frontend
npm install
npm run dev              # http://localhost:5173
```

### 5.4 Database migrations

```bash
cd backend
alembic revision --autogenerate -m "message"   # first revision
alembic upgrade head
alembic downgrade -1         # roll back one revision
alembic current             # show applied revision
```

The TimescaleDB hypertable is created by a migration that safely no-ops when
TimescaleDB/PostgreSQL is unavailable (e.g. SQLite in tests). See
`backend/MIGRATIONS_NOTES.md`.

### 5.5 Backup / restore

```bash
# Backup
docker compose exec db pg_dump -U emis emis > emis_backup.sql

# Restore
docker compose exec -T db psql -U emis emis < emis_backup.sql
```

Uploaded source files in `backend/uploads/` should be backed up alongside the database.

### 5.6 Tests

```bash
cd backend
# Windows, after installing Python 3.11:
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m pytest -q
```

The tests use an in-memory SQLite database, so no external database is required.
**Verified result:** `56 passed` (including 4 tests against the real supplied
Salacafe workbook). The venv has already been created in `backend/venv` on this
machine.

---

## 6. Implementation tracker

### Phase 1 — Project foundation ✅ code complete / 🟡 verification pending
- [x] Directory structure created
- [x] FastAPI app factory + configuration + extensions
- [x] All 17 SQLAlchemy models (full schema design)
- [x] Consistent JSON response helpers + application error handling
- [x] JWT login / logout / refresh / me / change-password
- [x] Audit logging service + login history
- [x] Alembic setup + idempotent seed script
- [x] Minimal read-only dashboard endpoints backed by real database counts
- [x] React + Vite + Tailwind skeleton, layout, login, protected routes
- [x] Dashboard page + audit log page (real API data only)
- [x] Docker Compose (PostgreSQL/TimescaleDB, Redis, FastAPI, Celery, Nginx) 
- [x] Tests for auth, system settings, audit and dashboard (written)
- [x] Backend tests + frontend production build verified locally

### Phase 2 — Station & sensor management ✅ code complete / 🟡 verification pending
- [x] Station CRUD with search, filters, pagination and archive-only delete
- [x] Station detail page: sensors, measurements, status history, maintenance, imports, change history
- [x] Sensor CRUD with per-station ports (no assumption of identical equipment)
- [x] Flexible sensor → measurement-type links with original column hints
- [x] Leaflet/OpenStreetMap station map with status-coloured markers and popups
- [x] Sensor health view (data freshness shown separately from connectivity)
- [x] Audit logging on all create/update/archive operations
- [x] Backend tests for station and sensor behaviour (written)
- [x] Backend tests + frontend production build verified locally
### Phase 3 — Data import (Excel/CSV, configurable mapping) ✅ code complete / 🟡 verification pending
- [x] Excel (.xlsx/.xlsm) and CSV upload with extension/size validation
- [x] Sheet inspection: dynamic header-row detection, Config 1 / Raw Config 1 / Metadata recognition
- [x] Metadata extraction and station auto-detection (never guessed from coordinates alone)
- [x] Header-driven column mapping with admin-editable preview (positions are never assumed)
- [x] Timestamp parsing with timezone handling (local observation time → UTC storage)
- [x] All source rows preserved as JSONB before processing
- [x] Duplicate detection (same station + sensor + type + observation time)
- [x] Validation flags: RH > 100%, zero soil moisture, negatives, missing/invalid timestamps
- [x] Import history, previews, errors and summaries
- [x] Celery background processing for files over 2 MB
- [x] Official API connector structure only (no invented endpoints)
- [x] Sample workbook generator + importer tests (written)
- [x] Worksheet selector in the import preview (for workbooks with multiple Config sheets)
- [x] Support for DENR-style telemetry CSV (Unix-ms timestamps + date/time columns)
- [x] Extra measurement types: water level, water temperature, EC, system temperature/battery voltage
- [ ] **Drop in the real Salacafe workbook to verify its exact headers/mapping**
- [x] Backend tests + frontend production build verified locally
### Phase 4 — Dashboards, analytics, trends, comparison ✅ code complete / 🟡 verification pending
- [x] Dashboard trend charts with station, date-range and interval filters
- [x] Seven series: temperature, humidity, wind speed, rainfall, solar, soil moisture, battery
- [x] Latest Monitoring page with real timestamps and station context
- [x] Analytics module: min/max/average/median/std/total/count/missing/completeness
- [x] Correct circular statistics for wind direction; rainfall uses SUM aggregation
- [x] Multi-station comparison using one compatible measurement type
- [x] Flexible two-period line-chart comparison (any two date ranges, aligned by elapsed time) with 15-min/hourly/daily buckets
- [x] CSV and Excel measurement export endpoints
- [x] Backend tests for trends, statistics, comparison and export (written)
- [x] Backend tests + frontend production build verified locally
### Phase 5 — Data quality, health, alerts ✅ code complete / 🟡 verification pending
- [x] Quality flag summary, filters, detail and resolution with remarks (source data untouched)
- [x] Station health snapshots with configurable freshness thresholds
- [x] Data freshness reported separately from equipment connectivity (NOT_REPORTED)
- [x] Battery alerts with deduplication and automatic recovery
- [x] Missing-data alerts, acknowledgement, resolution and alert history
- [x] Backend tests for quality, alerts and health (written)
- [x] Backend tests + frontend production build verified locally
### Phase 6 — Reports, maintenance, audit, settings ✅ code complete / 🟡 verification pending
- [x] Report generation in PDF (ReportLab) and Excel (OpenPyXL)
- [x] Report types: daily, weekly, monthly, performance, health, quality, rainfall, trends, comparison, imports, maintenance
- [x] Every report includes station, period, units, statistics, source, generation date and quality notes
- [x] Report history and download endpoints
- [x] Maintenance/calibration CRUD, upcoming/overdue calendar and audit trail
- [x] System settings editor (JSONB) with audit logging
- [x] Backend tests for reports and maintenance (written)
- [x] Backend tests + frontend production build verified locally
### Phase 7 — Future official API integration (structure only) ✅ scaffold ready
- [x] `integrations/excel_connector.py`, `csv_connector.py`
- [x] `integrations/official_api_connector.py` — explicit NotImplementedError; no endpoints invented
- [x] `integrations/normalizer.py` — all sources converge on the same measurement structure
- [x] `integrations/sync_service.py` — incremental/backfill method signatures reserved
- [x] `sync_logs` table ready for sync logs, retries, pagination and duplicate counts
- [ ] **Blocked: classic ZENTRA v4 token is valid; device `06-02478` is found but returns `403 User token does not have permission for given device`.** The account must be added to the device's ZENTRA Cloud Organization. Excel/CSV import remains the active data path. Connector stays as a documented stub.

### Phase 8 — Backend migration to FastAPI + weighted accomplishment reporting ✅ code complete / 🟡 verification pending
- [x] Full backend migrated from Flask to **FastAPI** (Pydantic validation, PyJWT, SQLAlchemy 2.0, Alembic)
- [x] Existing `/api/v1` endpoints preserved with the same JSON envelope
- [x] 10 new accomplishment tables (categories, indicators, targets, actuals, weight history, reports, snapshots, attachments, settings, audit)
- [x] Two-level weighting with frontend **and** backend validation (both totals must equal 100%)
- [x] Activity/Deliverable category scores and overall quarterly score
- [x] Annual calculation from summed quarterly actuals/targets (never an average of percentages)
- [x] Overachievement displayed but capped only for weighted contribution
- [x] Incremental actuals with unique entry references and duplicate prevention
- [x] Finalization validation, frozen snapshots, historical weight preservation and authorized revisions
- [x] Environmental data completeness as a separate technical KPI
- [x] PDF/Excel accomplishment reports integrated into the shared Reports history
- [x] Seven React pages under the "Quarterly Accomplishment" navigation item
- [x] Backend tests for formulas, weights, duplicates, snapshots, revisions and completeness (written)
- [x] Backend tests + frontend production build verified locally
- [x] Optional `seed_accomplishment_example.py` adds clearly-labelled **EXAMPLE** data (default year **2025**) so the calculations can be demonstrated without touching real data
- [x] User Management: admins can create/edit users, activate/deactivate accounts and reset passwords; every user can edit their own profile and password

---

## 7. Important notes / known limitations

1. **The real Salacafe workbook has now been supplied and inspected.** It was
   copied to `backend/tests/fixtures/salacafe_reference.xlsx`. Findings:
   sheets are `Config 1`, hidden `Raw Config 1` and `Metadata`; 220 data rows;
   `Config 1` has corrupted header labels (`System.Xml.XmlElement`) so the
   importer recovers them from `Raw Config 1` by header alignment; the `Metadata`
   sheet supplies station code `06-02478`, Salacafe, DENRFMB-WATERSHED, serial
   `929`, interval 900 s, lat/lon, timezone `UTC+08:00`, logger time and the
   port-to-sensor list. All of this is stored in `ImportBatch.detected_metadata`
   and shown in the import preview. Port banners in row 1 are recovered too, so
   the two soil-water columns (Ports 5 and 6) can be mapped to separate sensors
   instead of collapsing into one duplicate.
2. **Both sides were verified locally:** backend `56 passed` (Python 3.11.9 in
   `backend/venv`) and frontend `npm run build` succeeds (Node 26 / Vite 5).
   Note: on this machine `npm.ps1` is blocked by PowerShell's execution policy,
   so use `npm.cmd` from PowerShell, or run npm from Command Prompt.
3. JWT logout uses a process-local blocklist in `utils/security.py`. For
   multi-worker production, switch it to Redis (Redis is already in Compose).
4. Data freshness ≠ equipment connectivity. A late Excel upload will be shown
   as "data delayed", not as "station offline" (implemented in Phase 5).
5. The Phase 1 dashboard endpoints (`/api/v1/dashboard/*`) intentionally return
   only real database counters and the latest stored measurements. Charts,
   trends and statistics come in Phase 4. Empty tables produce empty states,
   never invented numbers.
6. All navigation items are active except the officially-blocked future API work.
   "Quarterly Accomplishment" opens a dashboard with seven section tabs/pages.
7. Archiving a station/sensor sets an `is_archived` flag. It never issues a SQL
   DELETE against stations or measurements, so historical data is preserved.
8. **Database choice:** local development currently uses SQLite
   (`backend/emis_dev.db`) because Docker/PostgreSQL was unavailable. The code
   supports PostgreSQL unchanged — set `DATABASE_URL` in `backend/.env` to
   `postgresql+psycopg2://user:password@host:5432/emis` and run
   `alembic revision --autogenerate -m "Initial schema"` then `alembic upgrade head`.
   PostgreSQL is recommended on the server for multi-user access, backups and
   TimescaleDB time-series features. SQLite is fine for a single-user local setup.

   To move the existing local data to PostgreSQL, create an empty database and
   run the copy script from `backend/` (it reads the destination from
   `DATABASE_URL`, never modifies the source, and verifies row counts):
   ```
   python scripts/migrate_to_postgresql.py
   ```
   The script creates the schema from the SQLAlchemy models, copies every table
   in foreign-key-safe order in batches, resets primary-key sequences, and
   fails safely if the target already contains EMIS tables.

9. **Dashboard counters:** "Quality warnings" counts *distinct open issues*
   (station × parameter × rule) with WARNING/CRITICAL severity, not every
   flagged reading — a single mis-mapped column can otherwise generate tens of
   thousands of near-identical flags. Station health is refreshed after every
   import, and the dashboard includes an "Unknown" bucket so the status cards
   always add up to the active station total.

## Deploying to a server that already has PostgreSQL

You do **not** need to reset or recover the password of your existing database
user. Create a separate role for EMIS instead, so other sites keep working.

**1. On the server, create a dedicated role and database:**
```bash
sudo -u postgres psql
```
```sql
CREATE ROLE emis_app LOGIN PASSWORD 'choose-a-new-password';
CREATE DATABASE emis OWNER emis_app;
\c emis
GRANT ALL ON SCHEMA public TO emis_app;
\q
```
(If `sudo -u postgres psql` is unavailable, run the SQL with any account that
has `CREATEDB`/`CREATEROLE` privileges.)

**2. Copy the project to the server, then configure it:**
```bash
cp .env.example .env
```
Edit `.env`:
- `DATABASE_URL` — use `host.docker.internal` if PostgreSQL runs on the same
  server as Docker; otherwise use its remote host/IP. Use the `emis_app` role
  and the password you just chose.
- `SECRET_KEY` / `JWT_SECRET_KEY` — generate fresh values:
  `python -c "import secrets; print(secrets.token_hex(32))"`
- `CORS_ORIGINS` — the URL users will actually open.
- `FRONTEND_PORT` — any free host port (default `8080`). Port `5173` is only a
  host-side mapping and can simply be changed; nothing inside the container
  depends on it.

**3. Start the stack:**
```bash
docker compose -f docker-compose.server.yml up -d --build
```
This compose file deliberately does **not** start its own PostgreSQL or publish
Redis, so it cannot collide with the services already on your server. Open
`http://YOUR_SERVER:8080`.

**4. Load the local data (optional):**
Copy `backend/emis_dev.db` from your development machine into `backend/` on the
server, then run the one-off migration container (it reads `DATABASE_URL` from
the root `.env`; the source file is mounted read-only):
```bash
docker compose -f docker-compose.server.yml --profile migrate run --rm migrate
```
It copies every table in batches and verifies row counts. The source SQLite
file is never modified. Restart the stack afterwards so the backend sees the
newly created tables and seed data:
```bash
docker compose -f docker-compose.server.yml restart backend celery
```

If your PostgreSQL is published on port 5432 of the server, the default
`host.docker.internal:5432` in `.env.example` works as-is — the compose file
maps `host-gateway` for exactly this case. If your PostgreSQL container instead
publishes a different host port, change the port in `DATABASE_URL`.
