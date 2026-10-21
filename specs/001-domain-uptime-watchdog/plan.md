# Implementation Plan: Domain Uptime Watchdog

**Branch**: `001-domain-uptime-watchdog` | **Date**: 2026-10-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-domain-uptime-watchdog/spec.md`

## Summary

A local uptime monitor for four domains. A FastAPI app served by Uvicorn (`my_web_app/`, in its own venv) starts one asyncio loop per domain at startup; each loop sends a plain HTTP GET to `http://<domain>/` every 5 seconds (4 s timeout, no redirect following) and inserts the result into PostgreSQL (the existing Docker container on `localhost:5432`). On startup the server creates the `domain_watchdog` database if missing and applies versioned `.sql` migrations from `my_web_app/migrations/`, tracked in a `schema_migrations` table. A React + Vite + TypeScript dashboard (`frontend/`) polls the REST API every 5 seconds to show per-domain status, 1 h / 24 h uptime, and recent check history.

## Technical Context

**Language/Version**: Python 3.13 (backend, locally available), TypeScript 5.x on Node 22 (frontend)

**Primary Dependencies**: Backend: FastAPI, Uvicorn (`uvicorn[standard]`), httpx (async HTTP probes), asyncpg (PostgreSQL driver + pool), pydantic-settings (config from `.env`). Frontend: React 18, Vite 5, TypeScript.

**Storage**: PostgreSQL 17 in the existing Docker container (`pg17-ai`, port 5432, user `postgres`, password `password`), database `domain_watchdog` (auto-created). Plain SQL migrations applied at startup.

**Testing**: Backend: pytest + pytest-asyncio, respx (mock httpx), integration tests against the real local Postgres using a throwaway `domain_watchdog_test` database. Frontend: Vitest + React Testing Library.

**Target Platform**: Developer machine (macOS); browser dashboard on localhost.

**Project Type**: Web application (backend API + background worker in one process, SPA frontend).

**Performance Goals**: 4 domains × 1 check / 5 s = 0.8 inserts/s; ≥95% of scheduled checks recorded (SC-001); status endpoint < 2 s with 30 days of data (~2.1 M rows) (SC-004).

**Constraints**: Per-check timeout 4 s (< 5 s interval); domains checked independently (no shared blocking); migrations idempotent and safe on every restart; bind to `127.0.0.1` only; credentials via `.env`, not source.

**Scale/Scope**: Single operator, 4 domains, ~69 k rows/day, 3 API endpoints + health, 1 dashboard page.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template (only `[PRINCIPLE_N]` placeholders), so there are no ratified gates to evaluate. Default engineering gates applied instead:

| Gate | Status | Notes |
|------|--------|-------|
| Simplicity (no unnecessary projects/layers) | PASS | Two projects (API, SPA); worker runs inside the API process; no ORM, no message queue. |
| Testability | PASS | Probe, uptime calc, and migration runner are pure/isolated and unit-testable; contracts testable via OpenAPI. |
| Secrets not in source | PASS | DB credentials in `my_web_app/.env` (git-ignored), `.env.example` committed. |
| Observability | PASS | Structured logging of state transitions (FR-014) and DB errors; `/api/health` reports DB and scheduler state. |

**Post-design re-check (after Phase 1)**: PASS — design adds no new projects, layers, or dependencies beyond those listed above.

## Project Structure

### Documentation (this feature)

```text
specs/001-domain-uptime-watchdog/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── openapi.yaml     # Phase 1 output (REST contract for the dashboard)
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit-tasks - not created here)
```

### Source Code (repository root)

```text
my_web_app/                      # Backend (FastAPI + Uvicorn), own venv
├── venv/                        # python3 -m venv venv (git-ignored)
├── requirements.txt
├── requirements-dev.txt
├── .env.example                 # DATABASE_URL, CHECK_INTERVAL_SECONDS, CHECK_TIMEOUT_SECONDS, CORS_ORIGINS
├── migrations/
│   └── 001_init.sql             # domains + check_results tables, index, seed of 4 domains
├── app/
│   ├── main.py                  # FastAPI app, lifespan: ensure DB → migrate → start monitor
│   ├── config.py                # pydantic-settings Settings
│   ├── db.py                    # asyncpg pool, ensure_database()
│   ├── migrate.py               # apply migrations/*.sql in order, schema_migrations table, advisory lock
│   ├── monitor.py               # per-domain asyncio loops, probe(), state-change logging
│   ├── repository.py            # SQL: insert result, status summary, history
│   ├── schemas.py               # Pydantic response models (match contracts/openapi.yaml)
│   └── api.py                   # /api/health, /api/domains/status, /api/domains/{hostname}/checks
└── tests/
    ├── unit/                    # probe classification, uptime math, migration ordering
    ├── integration/             # migrate twice, insert/query against real Postgres
    └── contract/                # responses validated against openapi.yaml

frontend/                        # React + Vite + TypeScript
├── package.json
├── vite.config.ts               # dev proxy /api → http://127.0.0.1:8000
├── index.html
└── src/
    ├── main.tsx
    ├── App.tsx                  # layout, polling, error banner
    ├── api/client.ts            # typed fetch wrappers for the 3 endpoints
    ├── hooks/usePolling.ts      # interval fetch with abort + error state
    ├── components/
    │   ├── StatusTable.tsx      # one row per domain: badge, last check, latency, 1h/24h uptime
    │   └── CheckHistory.tsx     # last N checks for the selected domain
    └── __tests__/
```

**Structure Decision**: Web application layout with the backend in `my_web_app/` (the directory name from the requested setup steps, with its venv inside) and the dashboard in `frontend/`. The monitor runs as background tasks in the API process's lifespan, so one `uvicorn` command starts migrations, checks, and the API together.

## Complexity Tracking

No constitution violations; nothing to justify.
