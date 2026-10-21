# Tasks: Domain Uptime Watchdog

**Input**: Design documents from `/specs/001-domain-uptime-watchdog/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md

**Tests**: Included. plan.md (Testing) and quickstart.md (V6, V10, test suites) call for pytest, contract and Vitest tests. Write each story's tests first and confirm they fail before implementing.

**Organization**: Tasks are grouped by user story so each can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1, US2, US3 (maps to spec.md user stories)
- All backend paths are relative to the repo root `/Users/germanworldclub/Documents/domain_watchdog/`

## Path Conventions

- Backend: `my_web_app/app/`, `my_web_app/migrations/`, `my_web_app/tests/{unit,integration,contract}/`
- Frontend: `frontend/src/`, `frontend/src/__tests__/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create backend directory layout per plan.md: `my_web_app/app/` (with empty `__init__.py`), `my_web_app/migrations/`, `my_web_app/tests/unit/`, `my_web_app/tests/integration/`, `my_web_app/tests/contract/`
- [X] T002 [P] Create `my_web_app/requirements.txt` (fastapi, uvicorn[standard], httpx, asyncpg, pydantic-settings) and `my_web_app/requirements-dev.txt` (pytest, pytest-asyncio, respx, openapi-core or jsonschema, pyyaml); create the venv with `python3 -m venv my_web_app/venv` and install both files
- [X] T003 [P] Create `my_web_app/.env.example` with `DATABASE_URL=postgresql://postgres:password@localhost:5432/domain_watchdog`, `CHECK_INTERVAL_SECONDS=5`, `CHECK_TIMEOUT_SECONDS=4`, `CORS_ORIGINS=http://localhost:5173`; copy to `my_web_app/.env`; add `.gitignore` at repo root ignoring `my_web_app/venv/`, `my_web_app/.env`, `__pycache__/`, `frontend/node_modules/`, `frontend/dist/`
- [X] T004 [P] Add pytest config `my_web_app/pytest.ini` (`asyncio_mode = auto`, `testpaths = tests`) and a `my_web_app/tests/conftest.py` fixture that creates/drops the throwaway database `domain_watchdog_test` on the local Postgres and yields its DSN
- [X] T005 [P] Scaffold the frontend in `frontend/` (Vite React + TypeScript: `package.json`, `tsconfig.json`, `index.html`, `src/main.tsx`); add Vitest, @testing-library/react, @testing-library/jest-dom, jsdom as dev dependencies and a `test` script; run `npm install`
- [X] T006 [P] Configure `frontend/vite.config.ts` with dev server on port 5173, `/api` proxy to `http://127.0.0.1:8000`, and Vitest `environment: 'jsdom'`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Config, database bootstrap, migrations and app skeleton that every story depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Implement `Settings` (pydantic-settings, reads `my_web_app/.env`: `database_url`, `check_interval_seconds=5`, `check_timeout_seconds=4`, `cors_origins`) in `my_web_app/app/config.py`
- [X] T008 Write `my_web_app/migrations/001_init.sql`: `domains` and `check_results` tables exactly per data-model.md (constraints, CHECKs, FK ON DELETE CASCADE), index `(domain_id, checked_at DESC)`, all with `IF NOT EXISTS`; seed the four domains (german-emirates-club.com, german-industry-club.com, german-medical-society.com, angels-bureau.com) with display names using `ON CONFLICT (hostname) DO NOTHING`
- [X] T009 Implement `ensure_database(dsn)` (connect to `postgres` maintenance DB, `CREATE DATABASE domain_watchdog` only if missing in `pg_database`) and `create_pool(dsn)` (asyncpg, min 1, max 5) in `my_web_app/app/db.py`
- [X] T010 Implement the migration runner in `my_web_app/app/migrate.py`: take `pg_advisory_lock`, create `schema_migrations(version text primary key, applied_at timestamptz not null default now())`, apply each unapplied `migrations/NNN_*.sql` in filename order, one transaction per file together with its `schema_migrations` insert, release the lock; log "already up to date" when nothing to apply; raise on any error
- [X] T011 Create the FastAPI app skeleton in `my_web_app/app/main.py`: `lifespan` that runs `ensure_database` → creates pool → `migrate` (store pool on `app.state`; raise on failure so the server never runs without storage), closes pool on shutdown; add CORS middleware from `settings.cors_origins`; include router from `app/api.py`
- [X] T012 [P] Create `my_web_app/app/api.py` with an empty `APIRouter(prefix="/api")` and `my_web_app/app/repository.py` with module docstring only (functions are added per story)
- [X] T013 [P] Implement typed fetch wrappers base in `frontend/src/api/client.ts` (`getJson<T>(path, signal)` that throws on non-2xx/network error; endpoint-specific functions and types are added in US2/US3)
- [X] T014 [P] Implement `usePolling(fn, intervalMs)` in `frontend/src/hooks/usePolling.ts`: calls `fn(signal)` immediately and every interval, skips a tick if the previous call is in flight, aborts on unmount, returns `{ data, error, lastUpdated }` keeping the last good data when an error occurs

**Checkpoint**: Foundation ready — user stories can begin

---

## Phase 3: User Story 1 - Continuous availability checks are recorded (Priority: P1) 🎯 MVP

**Goal**: On server start, storage is created automatically and every active domain is probed every 5 s with each result persisted.

**Independent Test**: Start uvicorn against an empty Postgres, wait 30 s; `check_results` has ~6 rows per domain (24 total) with timestamp, outcome, and response time or error. Restart 5 times with no errors and history preserved.

### Tests for User Story 1 ⚠️ (write first, must fail)

- [X] T015 [P] [US1] Unit tests for `probe()` classification in `my_web_app/tests/unit/test_probe.py` using respx: 200 → up; 301 (not followed) → up; 404 → down `http_404`; 503 → down `http_503`; timeout → `timeout`; DNS failure → `dns_error`; connection refused → `connection_error`; other exception → `error: <ExceptionType>`; assert invariant `is_up ⇒ status_code not null and error null`
- [X] T016 [P] [US1] Unit tests for the scheduler in `my_web_app/tests/unit/test_monitor_isolation.py`: a hanging domain does not delay other domains' cadence (V10); an overrunning check skips to the next future slot instead of bursting; state-transition logging emits WARNING "DOWN" on up→down and "RECOVERED" on down→up and nothing on unchanged state (FR-014)
- [X] T017 [P] [US1] Unit test for migration ordering/selection logic in `my_web_app/tests/unit/test_migrate_order.py` (files sorted by name, already-applied versions skipped)
- [X] T018 [P] [US1] Integration tests in `my_web_app/tests/integration/test_migrate.py` against `domain_watchdog_test`: run migrations twice → no error, one `schema_migrations` row per file, exactly 4 seeded domains; insert synthetic `check_results` and verify CHECK constraints reject status_code 99 and negative response time (V1, V2, SC-005)

### Implementation for User Story 1

- [X] T019 [US1] Implement `ProbeResult` dataclass and `async probe(client, hostname, timeout)` in `my_web_app/app/monitor.py`: `GET http://<hostname>/`, `follow_redirects=False`, 4 s timeout, `User-Agent: domain-watchdog/1.0`, response time via `time.perf_counter()`, classification per the data-model.md table (depends on T015)
- [X] T020 [US1] Add `insert_check_result(pool, domain_id, result)` and `list_active_domains(pool)` to `my_web_app/app/repository.py`
- [X] T021 [US1] Implement the per-domain loop and `Monitor` class (start/stop, `running` flag) in `my_web_app/app/monitor.py`: one `asyncio.Task` per active domain using fixed-cadence deadlines (`next_run += interval`, skip to next future slot on overrun), shared `httpx.AsyncClient`, catch-and-log DB insert errors so the loop keeps running and resumes when the DB returns, last-state tracking initialised from the latest stored row, WARNING log on up↔down transitions (FR-014) (depends on T019, T020)
- [X] T022 [US1] Wire the monitor into `lifespan` in `my_web_app/app/main.py`: after migrations, build `Monitor` from active domains and start it; cancel tasks and close the `httpx` client on shutdown; keep `Monitor` on `app.state`
- [X] T023 [US1] Add `GET /api/health` in `my_web_app/app/api.py` returning `{status, database, monitor}` per the `Health` schema (200 when ok, 503 when DB unreachable via `SELECT 1` or monitor stopped); add the `Health` model to `my_web_app/app/schemas.py`
- [ ] T024 [US1] Validate manually per quickstart V1–V3 and V6: start `uvicorn app.main:app --host 127.0.0.1 --port 8000` from `my_web_app/`, check `\dt`, row counts after 60 s (≥ 11 per domain), and 5 consecutive restarts without errors

**Checkpoint**: US1 is functional and testable on its own — MVP

---

## Phase 4: User Story 2 - See current status of every domain at a glance (Priority: P2)

**Goal**: Dashboard shows up/down, last check, latest latency and 1 h / 24 h uptime per domain, auto-refreshing every 5 s, with a clear error state when the backend is unreachable.

**Independent Test**: With the watchdog running, open http://localhost:5173 and verify four rows matching stored data and updating without reload; stop uvicorn and see the "cannot reach watchdog service" banner within 10 s.

### Tests for User Story 2 ⚠️ (write first, must fail)

- [X] T025 [P] [US2] Contract test in `my_web_app/tests/contract/test_status_contract.py`: `GET /api/domains/status` response validates against `DomainStatus`/list schema in `specs/001-domain-uptime-watchdog/contracts/openapi.yaml`, including null fields for a domain with no checks
- [X] T026 [P] [US2] Integration test in `my_web_app/tests/integration/test_status_queries.py`: with synthetic rows, assert latest-check fields, `uptime_1h`/`uptime_24h` = up ÷ total × 100 within each window, `checks_24h`, and NULL uptime (not 0) for a domain with no checks (FR-013)
- [X] T027 [P] [US2] Frontend tests in `frontend/src/__tests__/StatusTable.test.tsx` (Vitest + RTL): renders up, down, "no data yet" (null `is_up`/uptime), and the unreachable-service error banner with last-updated time

### Implementation for User Story 2

- [X] T028 [P] [US2] Add `DomainStatus` and `StatusResponse` Pydantic models (fields and nullability per openapi.yaml) to `my_web_app/app/schemas.py`
- [X] T029 [US2] Add `get_status_summary(pool)` to `my_web_app/app/repository.py`: one query using `DISTINCT ON (domain_id) ... ORDER BY domain_id, checked_at DESC` for latest check and `count(*) FILTER (WHERE is_up) * 100.0 / NULLIF(count(*),0)` over 1 h and 24 h windows, plus `checks_24h`; active domains only, ordered by hostname (depends on T028)
- [X] T030 [US2] Add `GET /api/domains/status` in `my_web_app/app/api.py` returning `{generated_at, interval_seconds, domains}` (depends on T029)
- [X] T031 [P] [US2] Add TypeScript types (`DomainStatus`, `StatusResponse`) and `fetchStatus(signal)` to `frontend/src/api/client.ts`
- [X] T032 [P] [US2] Implement `StatusTable` in `frontend/src/components/StatusTable.tsx`: one row per domain with up/down badge, "no data yet" when `is_up` is null, last check time, latest response time, 1 h / 24 h uptime (or "no data"); rows are selectable via an `onSelect(hostname)` prop
- [X] T033 [US2] Implement `App.tsx` in `frontend/src/App.tsx` and mount in `frontend/src/main.tsx`: `usePolling(fetchStatus, 5000)`, render `StatusTable`, and an error banner "Cannot reach watchdog service" showing last-updated time when polling fails (FR-012) (depends on T031, T032)
- [ ] T034 [US2] Validate manually per quickstart V4, V7, V8 (status curl output, dashboard refresh every ~5 s, backend-down banner and recovery) and check status endpoint latency < 2 s

**Checkpoint**: US1 and US2 both work independently

---

## Phase 5: User Story 3 - Review a domain's recent check history (Priority: P3)

**Goal**: Selecting a domain shows its latest 100 checks, newest first, with failures visually distinct.

**Independent Test**: Click a domain and verify the list matches the most recent stored records (newest first); failed checks are visually distinct.

### Tests for User Story 3 ⚠️ (write first, must fail)

- [X] T035 [P] [US3] Contract test in `my_web_app/tests/contract/test_checks_contract.py`: `GET /api/domains/{hostname}/checks` 200 validates against openapi.yaml; unknown hostname → 404 `Error`; `limit=5000` and `limit=0` → 422; default limit is 100
- [X] T036 [P] [US3] Integration test in `my_web_app/tests/integration/test_history_query.py`: ordering newest first and `limit` respected against synthetic rows
- [X] T037 [P] [US3] Frontend test in `frontend/src/__tests__/CheckHistory.test.tsx`: renders rows newest first with time, outcome, status code, response time, error; failed rows carry a distinct class/marker

### Implementation for User Story 3

- [X] T038 [P] [US3] Add `CheckResult` and `ChecksResponse` models to `my_web_app/app/schemas.py`
- [X] T039 [US3] Add `get_domain_by_hostname(pool, hostname)` and `list_checks(pool, domain_id, limit)` (ORDER BY `checked_at DESC` LIMIT) to `my_web_app/app/repository.py`
- [X] T040 [US3] Add `GET /api/domains/{hostname}/checks` in `my_web_app/app/api.py` with `limit: int = Query(100, ge=1, le=1000)`; 404 `{detail}` for unknown hostname (depends on T038, T039)
- [X] T041 [P] [US3] Add types and `fetchChecks(hostname, limit, signal)` to `frontend/src/api/client.ts`
- [X] T042 [P] [US3] Implement `CheckHistory` in `frontend/src/components/CheckHistory.tsx`: table of the last N checks with time, outcome, status code, response time, error; distinct styling for failed rows
- [X] T043 [US3] Integrate in `frontend/src/App.tsx`: track selected hostname from `StatusTable.onSelect`, poll `fetchChecks(selected, 100)` every 5 s via `usePolling`, render `CheckHistory` below the table (depends on T041, T042)
- [ ] T044 [US3] Validate manually per quickstart V5 and V9 (curl `limit=5`, unknown host 404, `limit=5000` 422; dashboard history view)

**Checkpoint**: All user stories independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T045 [P] Add a short `README.md` at repo root with the backend and frontend start commands from quickstart.md
- [ ] T046 Run full suites: `cd my_web_app && pytest` and `cd frontend && npm test`; fix any failures
- [X] T047 Verify the server binds only to `127.0.0.1` and no credentials are hard-coded in source (`grep -r "password" my_web_app/app frontend/src`)
- [ ] T048 Run the complete quickstart.md validation table (V1–V10) end to end and confirm SC-001–SC-005 (cadence ≥ 95% over 10 min, restart ×5, dashboard < 2 s)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none — start immediately
- **Foundational (Phase 2)**: depends on Setup — blocks all stories
- **US1 (Phase 3)**: depends on Foundational; MVP
- **US2 (Phase 4)**: depends on Foundational; backend part uses data written by US1 for real data but is testable with synthetic rows
- **US3 (Phase 5)**: depends on Foundational; shares `App.tsx`, `client.ts`, `schemas.py`, `api.py`, `repository.py` with US2, so sequence its edits after US2 (or merge carefully)
- **Polish (Phase 6)**: after the desired stories are complete

### Within Each Story

- Tests first and failing → models/schemas → repository → endpoints/components → integration → manual validation

### Task-level Dependencies

- T010 needs T008, T009; T011 needs T007, T009, T010
- T021 needs T019, T020; T022 needs T021; T023 needs T022
- T030 needs T029; T033 needs T031, T032
- T040 needs T038, T039; T043 needs T041, T042

## Parallel Opportunities

- Setup: T002–T006 after T001
- Foundational: T012, T013, T014 alongside T007–T011
- US1 tests T015–T018 together; US2 tests T025–T027 together; US3 tests T035–T037 together
- Frontend work (T031/T032, T041/T042) can run in parallel with backend work (T028–T030, T038–T040) within the same story

### Parallel Example: User Story 1

```text
Task: "Unit tests for probe() classification in my_web_app/tests/unit/test_probe.py"
Task: "Unit tests for the scheduler in my_web_app/tests/unit/test_monitor_isolation.py"
Task: "Unit test for migration ordering in my_web_app/tests/unit/test_migrate_order.py"
Task: "Integration tests in my_web_app/tests/integration/test_migrate.py"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup → Phase 2 Foundational
2. Phase 3 (US1) → stop and validate T024 (data accumulates, restarts are safe)

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → recorded history (MVP)
3. US2 → dashboard status view
4. US3 → per-domain history
5. Polish → full quickstart validation

## Notes

- [P] = different files, no dependencies on incomplete tasks
- `schemas.py`, `api.py`, `repository.py`, `client.ts` and `App.tsx` are touched by multiple stories; those tasks are not marked [P] against each other across stories
- Commit after each task or logical group
