# Data Model: Uptime Line Charts

No tables, columns, or migrations are added (see research R4 for an optional index). All data is derived from `check_results` and `domains` defined in [feature 001](../001-domain-uptime-watchdog/data-model.md).

## Derived: Chart Series (per domain + range)

| Field | Type | Notes |
|-------|------|-------|
| `hostname` | text | |
| `range` | enum `1h` \| `24h` \| `7d` | |
| `from`, `to` | timestamptz | Range window; `to` = request time |
| `bucket_seconds` | int | 30 / 300 / 1800 per range |
| `points[]` | list of Chart Point | Ordered by `t`; only buckets that contain checks |
| `downtime[]` | list of Downtime Period | Ordered by `started_at` |
| `gaps[]` | list of Gap | Missing-data intervals |
| `summary` | object | `down_periods`, `total_downtime_seconds`, `checks` (FR-009) |

### Chart Point (one bucket)

| Field | Type | Rule |
|-------|------|------|
| `t` | timestamptz | Bucket start |
| `avg_ms` | number \| null | Mean `response_time_ms` of **up** checks; null if none up in bucket |
| `max_ms` | integer \| null | Max over the same set |
| `checks` | int | All checks in bucket |
| `down` | int | Failed checks in bucket |

Failed checks never contribute to `avg_ms`/`max_ms` (FR-003).

### Downtime Period

| Field | Type | Rule |
|-------|------|------|
| `started_at` | timestamptz | First failed check of the run |
| `ended_at` | timestamptz | Last failed check of the run |
| `failed_checks` | int | |
| `errors` | list of text | Distinct `error` values in the run |
| `ongoing` | boolean | True if the run reaches the latest check and it is recent (< 30 s old) |

Run rule: consecutive rows with `is_up = false`, broken by any up row or any gap > 30 s.

### Gap

| Field | Type | Rule |
|-------|------|------|
| `started_at`, `ended_at` | timestamptz | Times of the two rows around a > 30 s silence; also covers range start/end when no checks exist near them |

### Summary
- `down_periods` = `len(downtime)`.
- `total_downtime_seconds` = sum of (`ended_at` − `started_at` + check interval) over periods, so a single failed check counts as one interval (5 s).
- `checks` = total checks in the range.

## Validation
- `range` outside the three values → 422. Unknown hostname → 404 (same as history endpoint).
- Empty range → `points`, `downtime`, `gaps` empty, `summary.checks = 0`; UI shows "no data for this period".
