# Research: Domain Uptime Watchdog

All Technical Context items were resolved; no NEEDS CLARIFICATION remain.

## R1. How to send the "raw HTTP request"

- **Decision**: `httpx.AsyncClient` shared per process, `GET http://<domain>/`, `follow_redirects=False`, `timeout=httpx.Timeout(4.0)`, custom `User-Agent: domain-watchdog/1.0`. Response time measured with `time.perf_counter()` around the request. Body is not read beyond what httpx needs (use `client.stream` / or just ignore content).
- **Rationale**: Plain HTTP with no redirect following matches the spec's definition of a raw probe (a 301 → HTTPS still proves the web server answers). httpx is async-native, pairs with FastAPI, and is trivially mockable with `respx` for tests.
- **Alternatives considered**: Raw `asyncio.open_connection` + hand-written `GET / HTTP/1.1` — more literally "raw" but re-implements status-line parsing, chunking and timeouts for no user benefit. `aiohttp` — equivalent, but httpx has better test tooling. ICMP ping — measures host reachability, not web availability, and needs privileges.

## R2. Scheduling checks every 5 seconds

- **Decision**: In FastAPI's `lifespan`, start one `asyncio.Task` per active domain. Each loop uses a fixed-cadence deadline (`next_run += interval; await asyncio.sleep(max(0, next_run - loop.time()))`), so a slow check doesn't drift the schedule; if a run overruns, skip to the next future slot rather than bursting. Tasks are cancelled on shutdown.
- **Rationale**: Satisfies FR-007 (independent domains) and the "no pile-up" edge case with zero extra dependencies. Timeout (4 s) < interval (5 s) guarantees no overlap per domain.
- **Alternatives considered**: APScheduler — extra dependency, overlap handling needs configuration. A single loop with `asyncio.gather` over all domains — one slow domain would delay others' next tick. Separate worker process/Celery — overkill for 0.8 inserts/s.

## R3. Database driver and access style

- **Decision**: `asyncpg` with a small pool (min 1, max 5); hand-written SQL in `repository.py`; no ORM.
- **Rationale**: Three queries total; asyncpg is the fastest async Postgres driver and runs multi-statement SQL files via `conn.execute()`, which the migration runner needs.
- **Alternatives considered**: SQLAlchemy 2 async + Alembic — heavy for 2 tables, and the user asked specifically for a SQL file applied at start. psycopg3 async — fine too; asyncpg chosen for simplicity of `execute(script)`.

## R4. Applying the SQL migration on server start

- **Decision**: Startup sequence in `lifespan`:
  1. Connect to the `postgres` maintenance DB and `CREATE DATABASE domain_watchdog` if `pg_database` has no such row (CREATE DATABASE cannot run in a transaction or use IF NOT EXISTS, hence the check).
  2. Connect to `domain_watchdog`, take `pg_advisory_lock(<constant>)`, create `schema_migrations(version text primary key, applied_at timestamptz)` if absent.
  3. For each `migrations/NNN_*.sql` sorted by filename not yet in `schema_migrations`: run file + insert version in one transaction.
  4. Release lock. Fail startup (raise) on any error so the server never runs checks without storage (spec edge case).
- **Rationale**: Idempotent across restarts (SC-005), ordered, transactional per file, safe if two server instances start at once. SQL also uses `IF NOT EXISTS` / `ON CONFLICT DO NOTHING` as a second safety net.
- **Alternatives considered**: Re-running one idempotent `schema.sql` every start — breaks once a non-idempotent change (ALTER/rename) is needed. Alembic/yoyo — extra tooling for a single SQL file. Using the default `postgres` database — works, but mixes app tables with whatever else lives in that shared container (it also hosts other projects), so a dedicated DB is cleaner.

## R5. Uptime calculation and query performance

- **Decision**: Compute on read with one query per request:
  `count(*) FILTER (WHERE is_up) * 100.0 / NULLIF(count(*),0)` over `checked_at >= now() - interval '1 hour'` and `'24 hours'`, plus `DISTINCT ON (domain_id) ... ORDER BY domain_id, checked_at DESC` for the latest check. Composite index `(domain_id, checked_at DESC)`.
- **Rationale**: 24 h window = ~17 k rows/domain, an index range scan well under SC-004's 2 s even with 30 days stored. `NULLIF` yields NULL → "no data" (FR-013).
- **Alternatives considered**: Pre-aggregated rollup table or TimescaleDB continuous aggregates (the container is timescaledb-ha) — premature for this volume; can be added later without API change.

## R6. Configuration and credentials

- **Decision**: `pydantic-settings` reading `my_web_app/.env`: `DATABASE_URL=postgresql://postgres:password@localhost:5432/domain_watchdog`, `CHECK_INTERVAL_SECONDS=5`, `CHECK_TIMEOUT_SECONDS=4`, `CORS_ORIGINS=http://localhost:5173`. `.env` git-ignored; `.env.example` committed with the same local values.
- **Rationale**: Keeps the user-provided local credentials out of source while needing zero setup beyond copying the example.

## R7. Frontend data fetching and dev wiring

- **Decision**: Vite React-TS template. Native `fetch` + a small `usePolling(fn, 5000)` hook with `AbortController`; Vite dev-server proxy `/api → http://127.0.0.1:8000` so the browser uses same-origin URLs. Backend also enables CORS for `http://localhost:5173` for direct calls. Polling pauses fetch overlap (skip tick if previous in flight). On fetch failure, show an error banner and mark data as stale with its last-updated time (FR-012).
- **Rationale**: 5 s polling satisfies FR-010/SC-003 (≤ 10 s visibility) with no extra libraries.
- **Alternatives considered**: TanStack Query — nice but unnecessary for 2 endpoints. WebSocket/SSE push — lower latency but more moving parts; polling meets the 10 s target.

## R8. Testing approach

- **Decision**: pytest-asyncio unit tests with `respx` covering up/down classification (200, 301, 404, 503, timeout, DNS/connect error). Integration tests create/drop `domain_watchdog_test` on the local container, run migrations twice, insert synthetic results, and assert uptime math. Contract tests validate API responses against `contracts/openapi.yaml` (via `openapi-core` or schema comparison with FastAPI's generated spec). Frontend: Vitest + RTL for StatusTable rendering states (up, down, no data, error).
- **Rationale**: Covers each FR at the cheapest level and uses the real Postgres the user already runs.
