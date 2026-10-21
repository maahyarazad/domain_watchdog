# Research: Uptime Line Charts

## R1 — Where to condense data
- **Decision**: Aggregate in PostgreSQL into fixed buckets by range: 1 h → 30 s (120), 24 h → 5 min (288), 7 d → 30 min (336). Per bucket: `avg`/`max` response time over **up** checks, `checks`, `down` count.
- **Rationale**: Keeps payload ≤ ~340 points per domain; the DB already holds the index `(domain_id, checked_at DESC)`; no client-side processing of ~480 k rows.
- **Alternatives**: Return raw rows (7 d = 483 k rows/domain, too heavy); client-side downsampling (still ships the rows); materialized rollup table (extra schema and write path, unnecessary at this scale).

## R2 — Not losing short outages when condensed
- **Decision**: Compute downtime periods separately from the **raw** rows (gaps-and-islands) and return them as an explicit list; buckets also carry a `down` count for tooltips.
- **Rationale**: FR-005 / US2-2 require a one-check outage to remain visible on a 7-day chart; averaged buckets would hide it.
- **Alternatives**: Mark buckets containing any failure (loses exact start/end, SC-002 needs ±1 interval).

## R3 — Downtime period and gap definition
- **Decision**: A downtime period is a run of consecutive `is_up = false` rows with no up row between and no inter-row gap > 30 s (6 × 5 s interval). A gap > 30 s between any two rows is "missing data" (watchdog stopped), returned as a `gaps` list and drawn as a broken line, never as downtime. Period `ended_at` = last failed check time; an unfinished outage has `ongoing = true`.
- **Rationale**: Matches the spec assumption; avoids reporting hours of downtime when the watchdog itself was off.
- **Alternatives**: Treat any silence as downtime (wrong when the monitor is off).

## R4 — Query cost at 7 days
- **Decision**: Use one window-function query per domain over the range (`lag()` for island starts). Existing index covers it. If measured > 3 s on 7 d of data, add `002_chart_index.sql` with a partial index `ON check_results (domain_id, checked_at) WHERE NOT is_up`, and compute islands from failed rows plus a count of up rows.
- **Rationale**: Start with no schema change (YAGNI); the optimisation is pre-identified and cheap.
- **Alternatives**: Add the index up front (premature).

## R5 — Chart rendering
- **Decision**: Hand-written inline SVG components (≈ 300 points × 4 charts), pure geometry helpers in `lib/chartGeometry.ts`.
- **Rationale**: No new dependency; full control over downtime bands with a hatch pattern (satisfies "not color alone", FR-002); trivially testable in jsdom.
- **Alternatives**: Recharts / uPlot / Chart.js (new dependency, jsdom canvas issues, harder to hatch bands).

## R6 — Per-chart scale and refresh
- **Decision**: Each chart has its own y-axis (0 → max response time, rounded up); all charts share the x-axis range. Reuse the existing `usePolling` hook at 15 s; keep the last good data and show the existing unreachable banner on error.
- **Rationale**: Meets the edge case "one slow domain must not flatten others" and FR-008.
- **Alternatives**: Shared y-axis (flattens fast domains).

## R7 — Request fan-out
- **Decision**: Four parallel requests (one per domain) instead of a combined endpoint.
- **Rationale**: Matches the existing `/domains/{hostname}/...` shape; a failing domain doesn't blank the others; asyncpg pool (max 5) handles four concurrent queries.
- **Alternatives**: Single `/charts?range=` returning all (couples failures, larger response).
