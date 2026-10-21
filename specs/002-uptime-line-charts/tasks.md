---

description: "Task list for Uptime Line Charts"
---

# Tasks: Uptime Line Charts

**Input**: Design documents from `/specs/002-uptime-line-charts/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md

**Tests**: Included, following the plan's test layout and the test style of feature 001 (pytest against the local Postgres test DB; Vitest + React Testing Library).

**Organization**: Grouped by user story. Backend lives in `server/`, frontend in `frontend/`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1, US2, US3 (maps to spec.md)

---

## Phase 1: Setup

- [X] T001 Confirm the baseline is green before changes: run `cd server && source venv/bin/activate && pytest` and `cd frontend && npm test`; note any pre-existing failures in this task's PR/commit message
- [X] T002 [P] Verify `server/.env` has a complete `DATABASE_URL` (user, password, host, port, `/domain_watchdog`) so the backend starts and integration tests can reach Postgres

---

## Phase 2: Foundational (blocks all user stories)

**Purpose**: Backend chart data and shared frontend types/fetcher. No user story can render without these.

- [X] T003 Add Pydantic models `ChartPoint`, `DowntimePeriod`, `Gap`, `ChartSummary`, `ChartResponse` to `server/app/schemas.py` exactly matching `contracts/openapi.yaml` (`range` is `Literal["1h","24h","7d"]`, `bucket_seconds` is `Literal[30,300,1800]`, `avg_ms` is `float | None`, `max_ms` is `int | None`)
- [X] T004 Add `RANGES = {"1h": (interval '1 hour', 30), "24h": (interval '24 hours', 300), "7d": (interval '7 days', 1800)}` and `get_chart_points(pool, domain_id, range_key)` to `server/app/repository.py`: bucket `check_results` with `to_timestamp(floor(extract(epoch from checked_at)/bucket)*bucket)`, returning `t`, `avg(response_time_ms) FILTER (WHERE is_up)`, `max(response_time_ms) FILTER (WHERE is_up)`, `count(*)`, `count(*) FILTER (WHERE NOT is_up)`, ordered by `t`, restricted to `checked_at >= now() - range`
- [X] T005 Add `get_downtime_and_gaps(pool, domain_id, range_key, interval_seconds)` to `server/app/repository.py`: one window-function query over raw rows in the range using `lag(checked_at)` and `lag(is_up)`; a new failed-run starts when the row is failed and (previous row is up, missing, or more than 30 s earlier); a gap is any pair of consecutive rows more than 30 s apart. Return `(downtime: list[dict], gaps: list[dict], total_checks: int)` per `data-model.md` (`started_at`, `ended_at`, `failed_checks`, distinct `errors`, `ongoing` = run reaches the latest row and that row is < 30 s old); compute `summary.total_downtime_seconds` as the sum of (`ended_at` − `started_at` + interval_seconds)
- [X] T006 [P] Add chart types (`ChartPoint`, `DowntimePeriod`, `Gap`, `ChartSummary`, `ChartResponse`, `ChartRange = '1h' | '24h' | '7d'`) and `fetchChart(hostname, range, signal?)` calling `/api/domains/{hostname}/chart?range=…` to `frontend/src/api/client.ts`
- [X] T007 Add route `GET /api/domains/{hostname}/chart` to `server/app/api.py`: `range: Literal["1h","24h","7d"] = Query("24h")` (invalid → 422), unknown hostname → 404 (reuse `get_domain_by_hostname` and the `ErrorOut` pattern from the history route), assemble `ChartResponse` with `from`/`to`, `bucket_seconds`, `points`, `downtime`, `gaps`, `summary` from T004/T005 using `settings.check_interval_seconds`

**Checkpoint**: `curl 'http://127.0.0.1:8000/api/domains/angels-bureau.com/chart?range=1h'` returns valid JSON (quickstart V1–V3).

---

## Phase 3: User Story 1 - Response time and downtime on a line chart (Priority: P1) 🎯 MVP

**Goal**: Each of the four domains shows a line chart (default range 24 h) with marked, hatched downtime periods, tooltips, and "no data" handling.

**Independent Test**: With history containing a failed run, open the dashboard; each domain has a chart, the failed run is a visibly hatched band whose start/end match the stored rows (quickstart V4–V7, V9, V10).

### Tests for User Story 1

- [X] T008 [P] [US1] Contract test in `server/tests/contract/test_chart_contract.py`: response shape matches `ChartResponse` for each range, default range is `24h` with `bucket_seconds` 300, `range=30d` → 422, unknown hostname → 404 (follow `test_checks_contract.py` and `helpers.py`)
- [X] T009 [P] [US1] Integration test in `server/tests/integration/test_chart_queries.py` using `seed_checks` from `server/tests/conftest.py`: (a) one failed check among many up checks yields exactly one downtime period with correct start/end even on `7d`; (b) a bucket with only failed checks has `avg_ms` null and `down` > 0 (never 0); (c) a >30 s silence appears in `gaps` and not in `downtime`; (d) no rows → empty lists and `summary.checks == 0`; (e) `summary.total_downtime_seconds` counts a single failed check as one interval
- [X] T010 [P] [US1] Unit test in `frontend/src/__tests__/chartGeometry.test.ts` for the helpers from T012: x/y scaling, niceMax rounding, line path split into separate segments at null `avg_ms` and at gaps, band x-extent for a downtime period (minimum visible width), empty input
- [X] T011 [P] [US1] Component test in `frontend/src/__tests__/UptimeChart.test.tsx`: renders domain name, summary (down periods, total downtime), one hatched band per downtime period, "no data for this period" when `points` is empty, and tooltip text (time, outcome, response time, error) on hover/focus of a point and of a band

### Implementation for User Story 1

- [X] T012 [US1] Create `frontend/src/lib/chartGeometry.ts` with pure helpers: `scaleX(t, from, to, width)`, `scaleY(ms, niceMax, height)`, `niceMax(maxMs)`, `buildLineSegments(points, gaps, …)` (new segment at null `avg_ms` and across gaps), `bandRect(period, from, to, width, minPx = 3)`, `formatDuration(seconds)`
- [X] T013 [US1] Create `frontend/src/components/UptimeChart.tsx`: props `{ data: ChartResponse }`; inline SVG with per-chart y-axis (0 → `niceMax`), x-axis time labels for the range, response-time polyline segments, `<pattern>` hatch fill for downtime bands plus a distinct stroke (not color alone), dimmed hatch-free missing-data gaps, header with hostname and `summary` (FR-009), empty state "no data for this period", and a tooltip for points and bands (FR-006); give band and point elements `tabIndex=0` and `aria-label` for accessibility
- [X] T014 [US1] Add chart styles (container, axes, hatch band, tooltip, responsive grid for 4 charts) to `frontend/src/index.css`, honoring the existing light/dark treatment in that file
- [X] T015 [US1] Update `frontend/src/App.tsx`: derive domain hostnames from the existing `status` data, fetch `fetchChart(hostname, '24h')` for each via `usePolling`, and render a grid of `UptimeChart` below `StatusTable` (extract a small `ChartGrid` component in `frontend/src/components/ChartGrid.tsx` if App grows beyond readability); show per-chart "Loading…" until first data

**Checkpoint**: US1 independently demonstrable (quickstart V4–V7, V9, V10).

---

## Phase 4: User Story 2 - Choose the time range (Priority: P2)

**Goal**: Operator switches between last hour, 24 hours, 7 days; all four charts follow.

**Independent Test**: Click each range; all charts' axes and data match (quickstart V2, V8; SC-005).

- [X] T016 [P] [US2] Component test in `frontend/src/__tests__/RangeSelector.test.tsx`: renders three options, marks the active one (`aria-pressed`), calls `onChange` with `'1h' | '24h' | '7d'`
- [X] T017 [P] [US2] Create `frontend/src/components/RangeSelector.tsx` (segmented button group, keyboard accessible) and its styles in `frontend/src/index.css`
- [X] T018 [US2] Wire range state in `frontend/src/App.tsx`: `useState<ChartRange>('24h')`, pass to `RangeSelector` and to the chart fetchers so all four charts use the same range; ensure switching keeps the previous chart visible (dimmed) until new data arrives, with no flash of the "no data" state
- [X] T019 [US2] Add an App-level test in `frontend/src/__tests__/App.test.tsx` (mock `fetch`): switching ranges issues requests with the new `range` for all four domains

**Checkpoint**: US1 + US2 work together.

---

## Phase 5: User Story 3 - Charts stay current (Priority: P3)

**Goal**: Charts refresh at least every 15 s and show the existing unreachable banner when the service is down.

**Independent Test**: Keep the dashboard open on 1 h, cause a domain to fail; the outage appears within 15 s; stopping uvicorn shows the banner (quickstart V11, V12).

- [X] T020 [US3] Set the chart polling interval to 15000 ms in `frontend/src/App.tsx` (restart polling when the range changes), keeping the last good data on error
- [X] T021 [US3] Show the existing "cannot reach watchdog service" message when any chart request errors (reuse the wording/component used by `StatusTable` in `frontend/src/components/StatusTable.tsx`) and mark charts as stale instead of presenting them as current
- [X] T022 [P] [US3] Test in `frontend/src/__tests__/App.test.tsx`: with fake timers, advancing 15 s triggers a new chart request; a rejected fetch shows the unreachable message and does not clear existing chart data

---

## Phase 6: Polish & Cross-Cutting

- [X] T023 Measure the 7-day query with ~7 days of data (seed a throwaway DB or use real data): all four chart requests must finish < 3 s total (SC-003). Result: 0.38 s for 7 d x 4 domains (481 k rows), so no index was added. If it had been slow, add `server/migrations/002_chart_index.sql` with `CREATE INDEX IF NOT EXISTS idx_check_results_down ON check_results (domain_id, checked_at) WHERE NOT is_up;` and adjust T005's query as described in `research.md` R4; add a migration test case in `server/tests/integration/test_migrate.py` if added
- [X] T024 [P] Update `README.md`: correct the backend path (`server/`, not `my_web_app/`) and add one line mentioning the charts and the `range` parameter
- [X] T025 [P] Run `cd frontend && npm run lint && npm run build` and fix any warnings introduced by this feature
- [ ] T026 Execute every row of `specs/002-uptime-line-charts/quickstart.md` (V1–V13) against the running app and record pass/fail at the bottom of that file

---

## Dependencies & Execution Order

- **Phase 1** → **Phase 2** → user stories. T003 precedes T004/T005/T007; T004 and T005 precede T007; T006 is independent of backend tasks.
- **US1 (P1)** depends only on Phase 2. **US2** depends on US1's `App.tsx` and chart components (T015). **US3** depends on US1 and touches the same `App.tsx` as US2 (do US2 then US3, or merge carefully).
- **Polish** after the stories it verifies; T023 can start once T007 is done.

### Within each story
- Tests (T008–T011, T016, T022) are written first and should fail before implementation.
- T012 (geometry) → T013 (component) → T014 (styles) → T015 (App).

### Parallel opportunities
- Phase 2: T006 alongside T003–T005.
- US1: T008, T009, T010, T011 together; T012 can start alongside the tests.
- US2: T016 and T017 together.
- Polish: T024 and T025 together.

### Parallel example — User Story 1 tests

```text
T008 server/tests/contract/test_chart_contract.py
T009 server/tests/integration/test_chart_queries.py
T010 frontend/src/__tests__/chartGeometry.test.ts
T011 frontend/src/__tests__/UptimeChart.test.tsx
```

## Implementation Strategy

- **MVP**: Phases 1–3 (through T015) deliver the stated goal — per-domain line charts with downtime marked — on the default 24 h range.
- **Incremental**: add US2 (range selector), then US3 (15 s refresh and error state), validating with the quickstart rows named in each checkpoint.
- Keep the diff small: no new dependencies, no schema change unless T023 shows it is needed.
