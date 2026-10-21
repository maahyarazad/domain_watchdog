# Implementation Plan: Uptime Line Charts

**Branch**: `002-uptime-line-charts` | **Date**: 2026-10-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-uptime-line-charts/spec.md`

## Summary

Add one response-time line chart per monitored domain to the existing dashboard, built from the `check_results` rows already stored by feature 001. A new read-only endpoint, `GET /api/domains/{hostname}/chart?range=1h|24h|7d`, returns (a) response-time points aggregated into fixed time buckets so the payload stays small for any range, and (b) a list of downtime periods computed from the raw rows, so short outages are never lost when data is condensed. The React dashboard renders each series as a dependency-free SVG line chart with shaded, hatched downtime bands, a shared range selector (default 24 h), tooltips, and the existing 5 s polling hook. No new tables, no new collected data, no new runtime dependencies.

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript on Node 22 (frontend) — unchanged from 001.

**Primary Dependencies**: Existing only: FastAPI, asyncpg, pydantic (backend); React 19, Vite (frontend). Charts are hand-rendered inline SVG; no charting library added.

**Storage**: Existing PostgreSQL `domain_watchdog` database; read-only queries on `domains` and `check_results`. No schema change required (see research R4 for an optional index).

**Testing**: Backend pytest (+ integration tests against the throwaway test DB with synthetic rows); frontend Vitest + React Testing Library.

**Target Platform**: macOS developer machine; browser on localhost.

**Project Type**: Web application (existing `server/` API + `frontend/` SPA).

**Performance Goals**: All four charts load < 3 s on 7 days of history (~483 k rows/domain) (SC-003); range switch < 2 s (SC-005); refresh every 15 s (FR-008).

**Constraints**: Chart payload bounded (≤ ~400 points/domain regardless of range); downtime periods must survive aggregation; failed checks never plotted as 0 ms; gaps in checking shown as missing data, not downtime.

**Scale/Scope**: 4 domains, 3 ranges, 1 new endpoint, 2 new frontend components.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, so no ratified gates exist. Same default gates as feature 001:

| Gate | Status | Notes |
|------|--------|-------|
| Simplicity | PASS | One endpoint, two components, zero new dependencies or tables. |
| Testability | PASS | Bucketing/downtime logic is SQL + a pure function; chart geometry is a pure function; both unit/integration testable with synthetic rows. |
| Secrets not in source | PASS | No new configuration or credentials. |
| Observability | PASS | Existing logging; query failures surface as 5xx and the dashboard error state. |

**Post-design re-check**: PASS — design adds no projects, tables, or dependencies.

## Project Structure

### Documentation (this feature)

```text
specs/002-uptime-line-charts/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── openapi.yaml
├── checklists/
│   └── requirements.md
└── tasks.md             # created later by /speckit-tasks
```

### Source Code (repository root)

```text
server/
├── app/
│   ├── api.py               # + GET /api/domains/{hostname}/chart
│   ├── repository.py        # + get_chart_series(), get_downtime_periods()
│   └── schemas.py           # + ChartResponse, ChartPoint, DowntimePeriod
└── tests/
    ├── contract/            # + chart endpoint contract test
    └── integration/         # + bucketing & downtime-period tests with synthetic rows

frontend/
└── src/
    ├── api/client.ts        # + fetchChart(hostname, range)
    ├── components/
    │   ├── UptimeChart.tsx  # SVG line chart + downtime bands + tooltip
    │   └── RangeSelector.tsx
    ├── lib/chartGeometry.ts # pure scale/path/gap helpers
    ├── App.tsx              # + range state, chart grid
    └── __tests__/           # + UptimeChart, RangeSelector, chartGeometry tests
```

**Structure Decision**: Extend the existing `server/` and `frontend/` projects in place. Following the 001 layout, SQL stays in `repository.py` and routes in `api.py`.

## Complexity Tracking

No constitution violations to justify.
