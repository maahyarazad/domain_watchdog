# Quickstart: Uptime Line Charts

Validation guide for feature 002. Prerequisites: backend and frontend running as described in the project `README.md` (backend in `server/`), Postgres reachable, at least a few minutes of checks stored.

| # | Check (spec ref) | Command / action | Expected |
|---|------------------|------------------|----------|
| V1 | Endpoint shape (FR-001, FR-005) | `curl -s 'http://127.0.0.1:8000/api/domains/angels-bureau.com/chart?range=1h'` | JSON matching [contracts/openapi.yaml](contracts/openapi.yaml); `bucket_seconds` 30; ≤ 120 points |
| V2 | Range options (FR-004) | Repeat with `range=24h` and `range=7d` | `bucket_seconds` 300 / 1800; default (no param) behaves as `24h` |
| V3 | Validation | `range=30d` → 422; unknown hostname → 404 | Status codes as stated |
| V4 | Downtime survives condensing (FR-002, US2-2) | Insert 1 failed row among up rows (synthetic, test DB), request `range=7d` | `downtime` has one period with matching start/end |
| V5 | No zero plotting (FR-003) | Bucket with only failed checks | `avg_ms` null, `down` > 0 |
| V6 | Gaps vs downtime (FR-007) | Stop the server 2 min, restart | `gaps` lists the pause; no `downtime` period for it |
| V7 | Dashboard charts (US1) | Open http://localhost:5173 | Four charts, domain name and downtime summary on each, default range 24 h |
| V8 | Range selector (US2) | Click 1 h / 24 h / 7 d | All four charts update together |
| V9 | Tooltip (FR-006) | Hover a point / downtime band | Time, outcome, response time, error shown |
| V10 | Hatched band (FR-002) | View a chart with an outage | Band has hatch pattern, visible without color |
| V11 | Live refresh (US3) | Block a domain (e.g. hosts entry) and wait | New downtime shown within 15 s |
| V12 | Backend down (FR-008) | Stop uvicorn | "cannot reach watchdog service" banner |
| V13 | Performance (SC-003/SC-005) | Time V1 for 7d with ~7 days of data | < 3 s for all four charts together |

Automated: `cd server && pytest` and `cd frontend && npm test`.
