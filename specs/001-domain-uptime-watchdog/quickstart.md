# Quickstart & Validation: Domain Uptime Watchdog

Contracts: [contracts/openapi.yaml](contracts/openapi.yaml) · Data model: [data-model.md](data-model.md)

## Prerequisites

- Python 3.13, Node 22, npm
- PostgreSQL container running on `localhost:5432` (user `postgres`, password `password`) — check with `docker ps`
- Outbound internet access on port 80

## 1. Backend setup and start

```bash
cd my_web_app
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate.bat
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Expected log**: database `domain_watchdog` created (first run only) → migration `001_init` applied (first run only, "already up to date" afterwards) → 4 monitor tasks started.

## 2. Frontend setup and start

```bash
cd frontend
npm install
npm run dev                          # http://localhost:5173
```

## Validation scenarios

| # | Scenario (spec ref) | Steps | Expected |
|---|---------------------|-------|----------|
| V1 | Auto migration (US1-AS1, FR-006) | First start against a container without `domain_watchdog` | `psql -h localhost -U postgres -d domain_watchdog -c '\dt'` lists `domains`, `check_results`, `schema_migrations`; `domains` has 4 rows |
| V2 | Idempotent restart (US1-AS4, SC-005) | Stop and restart uvicorn 5 times | No errors; `schema_migrations` still has one row per migration; `check_results` count only grows |
| V3 | 5-second cadence (FR-002, SC-001) | Run 60 s, then `SELECT d.hostname, count(*) FROM check_results c JOIN domains d ON d.id=c.domain_id WHERE checked_at > now()-interval '60 seconds' GROUP BY 1;` | ~12 per domain (≥ 11) |
| V4 | Status API (FR-008) | `curl -s http://127.0.0.1:8000/api/domains/status` | 4 entries, each with `is_up`, `last_checked_at`, `uptime_1h`, `uptime_24h` per contract |
| V5 | History API (FR-009) | `curl -s 'http://127.0.0.1:8000/api/domains/angels-bureau.com/checks?limit=5'` | 5 checks, newest first; unknown host → 404; `limit=5000` → 422 |
| V6 | Failure recorded (US1-AS3, FR-004) | Run tests: `pytest tests/unit -k probe` (mocked timeout / DNS / 503) | Down results with `error` = `timeout` / `dns_error` / `http_503` |
| V7 | Dashboard (US2-AS1, FR-010) | Open http://localhost:5173 | 4 rows with up/down badge, last check, latency, 1 h / 24 h uptime; updates every ~5 s without reload |
| V8 | Backend down (US2-AS3, FR-012) | Stop uvicorn with dashboard open | Within 10 s an error banner "cannot reach watchdog service" appears; recovers when restarted |
| V9 | History view (US3) | Click a domain | Last 100 checks, newest first, failures visually distinct |
| V10 | Isolation (FR-007) | `pytest tests/unit -k isolation` (one domain mocked to hang) | Other domains keep a 5 s cadence |

## Test suites

```bash
cd my_web_app && pytest                 # unit + integration (needs the local Postgres) + contract
cd frontend && npm test                 # Vitest
```
