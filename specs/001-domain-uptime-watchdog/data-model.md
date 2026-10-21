# Data Model: Domain Uptime Watchdog

Database: `domain_watchdog` on the local PostgreSQL 17 container (auto-created at startup). All timestamps are `timestamptz` (UTC).

## Entity: `domains` (Monitored Domain)

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | `smallint` identity | PK | |
| `hostname` | `text` | NOT NULL, UNIQUE, lowercase, matches `^[a-z0-9.-]+$` | e.g. `german-emirates-club.com` |
| `display_name` | `text` | NOT NULL | Shown in dashboard |
| `is_active` | `boolean` | NOT NULL, default `true` | Only active domains get a monitor loop |
| `created_at` | `timestamptz` | NOT NULL, default `now()` | |

**Seed (in `001_init.sql`, `ON CONFLICT (hostname) DO NOTHING`)**: `german-emirates-club.com`, `german-industry-club.com`, `german-medical-society.com`, `angels-bureau.com` (FR-001).

## Entity: `check_results` (Check Result)

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | `bigint` identity | PK | ~69 k rows/day |
| `domain_id` | `smallint` | NOT NULL, FK → `domains.id` ON DELETE CASCADE | |
| `checked_at` | `timestamptz` | NOT NULL, default `now()` | Time the request was started |
| `is_up` | `boolean` | NOT NULL | Rule below (FR-003) |
| `status_code` | `smallint` | NULL, CHECK 100–599 | NULL if no HTTP response |
| `response_time_ms` | `integer` | NULL, CHECK ≥ 0 | NULL if no response |
| `error` | `text` | NULL | e.g. `timeout`, `dns_error`, `connection_error`, `http_503` |

**Index**: `(domain_id, checked_at DESC)` — serves latest-check, window uptime, and history queries.

**Validation / classification rules** (applied in `monitor.py` before insert):

| Probe outcome | `is_up` | `status_code` | `response_time_ms` | `error` |
|---------------|---------|---------------|--------------------|---------|
| Response, status < 400 | true | code | measured | NULL |
| Response, status ≥ 400 | false | code | measured | `http_<code>` |
| No response within 4 s | false | NULL | NULL | `timeout` |
| DNS resolution failure | false | NULL | NULL | `dns_error` |
| Connect refused/reset | false | NULL | NULL | `connection_error` |
| Any other exception | false | NULL | NULL | `error: <ExceptionType>` |

Invariant: `is_up = true` ⇒ `status_code IS NOT NULL AND error IS NULL`.

## Entity: `schema_migrations` (infrastructure)

| Field | Type | Constraints |
|-------|------|-------------|
| `version` | `text` | PK — migration filename stem, e.g. `001_init` |
| `applied_at` | `timestamptz` | NOT NULL, default `now()` |

Created by the migration runner itself (not by a migration file).

## Derived: Status Summary (not stored)

Computed per active domain on each `GET /api/domains/status`:

| Field | Source |
|-------|--------|
| `hostname`, `display_name` | `domains` |
| `is_up`, `status_code`, `response_time_ms`, `error`, `last_checked_at` | latest `check_results` row (NULL if none) |
| `uptime_1h`, `uptime_24h` | `100.0 * count(is_up) / count(*)` in window; NULL when count = 0 (FR-013) |
| `checks_24h` | row count in 24 h window |

## State Transitions (per domain, in-memory)

```
unknown ──first check──▶ up | down
up ──failed check──▶ down      (log WARNING "domain DOWN")
down ──successful check──▶ up  (log WARNING "domain RECOVERED")
```

The monitor keeps the last outcome per domain in memory (initialised from the latest stored row at startup) to emit FR-014 transition logs; no transition table is stored in v1.

## Relationships

`domains 1 ─── * check_results`
