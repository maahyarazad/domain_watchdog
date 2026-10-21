# Feature Specification: Domain Uptime Watchdog

**Feature Branch**: `001-domain-uptime-watchdog`

**Created**: 2026-10-21

**Status**: Draft

**Input**: User description: "Domain uptime watchdog: a Python FastAPI server (run with Uvicorn, in a venv inside a my_web_app-style backend directory) that, from this local machine, sends raw HTTP requests every 5 seconds to german-emirates-club.com, german-industry-club.com, german-medical-society.com and angels-bureau.com, and stores each check result (uptime) in a PostgreSQL database running in Docker (localhost:5432, user postgres, password password). A SQL migration file is applied automatically on server start. A React + Vite frontend consumes the server's API to display the uptime status of each domain."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Continuous availability checks are recorded (Priority: P1)

As the site operator, I start the watchdog on my local machine and, without any further action, it checks each of the four monitored domains every 5 seconds and keeps a permanent record of every check (whether the domain answered, how it answered, and how long it took).

**Why this priority**: Without a reliable history of checks there is nothing to display or analyze. This alone already delivers value: the operator can inspect the stored history to see when a domain was down.

**Independent Test**: Start the watchdog against an empty database, wait 30 seconds, and confirm that roughly 6 check records per domain (24 total) exist, each with a timestamp, outcome, and response time or error.

**Acceptance Scenarios**:

1. **Given** the watchdog is not running and the storage is empty, **When** the operator starts it, **Then** the storage structure is created automatically and checks begin without manual setup steps.
2. **Given** the watchdog is running, **When** 5 seconds pass, **Then** one new check record exists for each of the four domains.
3. **Given** a domain does not respond or the connection fails, **When** its check runs, **Then** a record is stored marking it as down with the reason (e.g., timeout, DNS failure, connection refused).
4. **Given** the watchdog was stopped and restarted, **When** it starts again, **Then** existing history is preserved and setup does not fail or duplicate structures.

---

### User Story 2 - See current status of every domain at a glance (Priority: P2)

As the site operator, I open the dashboard in my browser and immediately see, for each of the four domains, whether it is currently up or down, when it was last checked, its latest response time, and its uptime percentage over recent periods.

**Why this priority**: This is the primary way the operator consumes the data; it turns raw records into an actionable view.

**Independent Test**: With the watchdog running and history present, open the dashboard and verify all four domains are listed with correct current status, last-check time, response time, and uptime percentages that match the stored records.

**Acceptance Scenarios**:

1. **Given** the watchdog has recorded checks, **When** the operator opens the dashboard, **Then** each domain shows an up/down indicator, last check time, latest response time, and uptime percentage for the last hour and last 24 hours.
2. **Given** the dashboard is open, **When** a domain's status changes, **Then** the dashboard reflects the change within 10 seconds without a manual page reload.
3. **Given** the watchdog backend is unreachable, **When** the dashboard tries to refresh, **Then** it shows a clear "cannot reach watchdog service" message instead of stale data presented as current.

---

### User Story 3 - Review a domain's recent check history (Priority: P3)

As the site operator, I select a domain and see its recent individual checks (time, outcome, status code, response time, error reason) so I can understand when and why it went down.

**Why this priority**: Useful for diagnosing incidents but not required to know current health.

**Independent Test**: Select a domain on the dashboard and verify the listed recent checks match the most recent stored records for that domain, newest first.

**Acceptance Scenarios**:

1. **Given** a domain has check history, **When** the operator selects it, **Then** the most recent 100 checks are shown newest first with time, outcome, status code (if any), response time (if any), and error reason (if any).
2. **Given** a domain had a period of failures, **When** the operator views its history, **Then** failed checks are visually distinguishable from successful ones.

---

### Edge Cases

- A check takes longer than the 5-second interval: the next scheduled check for that domain must not pile up behind it; a slow check is cut off by a timeout shorter than the interval and recorded as down (timeout).
- One domain hangs or errors: checks for the other domains continue unaffected and on schedule.
- The database is unavailable at startup: the watchdog reports a clear error and does not start checking silently without storing results.
- The database becomes unavailable while running: the watchdog logs the failure, keeps running, and resumes storing when the database returns (checks during the outage may be lost).
- A domain answers with a redirect (e.g., HTTP → HTTPS): treated as up, since the server responded.
- A domain answers with a server error (5xx) or client error (4xx): treated as down, with the status code stored.
- No checks yet exist for a domain (fresh start): the dashboard shows "no data yet" rather than 0% uptime.
- The local machine has no internet connection: all domains record as down with a network error; the dashboard shows them as down.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST monitor exactly these four domains by default: german-emirates-club.com, german-industry-club.com, german-medical-society.com, angels-bureau.com.
- **FR-002**: System MUST send a plain HTTP request from the local machine to each monitored domain every 5 seconds while running.
- **FR-003**: System MUST treat a check as **up** when the domain returns an HTTP response with a status code below 400, and **down** otherwise (status ≥ 400, timeout, DNS failure, connection error, or any other error).
- **FR-004**: System MUST abort any single check that has not completed within 4 seconds and record it as down with reason "timeout".
- **FR-005**: System MUST store every check result with: domain, check time, up/down outcome, HTTP status code (when received), response time in milliseconds (when received), and error reason (when failed).
- **FR-006**: System MUST create or update its storage structure automatically from a versioned migration file when the server starts, and MUST be safe to start repeatedly against an already-migrated database.
- **FR-007**: System MUST perform checks for different domains independently so a slow or failing domain does not delay checks of the others.
- **FR-008**: System MUST expose the current status summary for all domains: latest outcome, last check time, latest response time, and uptime percentage over the last 1 hour and last 24 hours.
- **FR-009**: System MUST expose the recent check history for a single domain, newest first, limited to a requested count (default 100, maximum 1000).
- **FR-010**: Dashboard MUST display the status summary for all four domains and refresh automatically at least every 5 seconds.
- **FR-011**: Dashboard MUST let the operator view the recent check history of a selected domain.
- **FR-012**: Dashboard MUST show a clear error state when the watchdog service cannot be reached.
- **FR-013**: Uptime percentage MUST be calculated as (number of up checks ÷ total checks) × 100 within the period, and shown as "no data" when the period has no checks.
- **FR-014**: System MUST log a warning whenever a domain changes state (up → down or down → up).

### Key Entities

- **Monitored Domain**: A website being watched. Attributes: hostname, display name, whether monitoring is active.
- **Check Result**: One availability probe of a domain at a moment in time. Attributes: domain, checked-at time, outcome (up/down), status code, response time, error reason. Many check results belong to one monitored domain.
- **Status Summary** (derived, not stored): Per-domain view of latest outcome, last check time, latest response time, and uptime percentages over defined periods.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Over any 10-minute window of normal operation, at least 95% of the expected checks (120 per domain) are recorded for each domain.
- **SC-002**: The operator can go from starting the watchdog to seeing all four domains' status on the dashboard in under 1 minute, with no manual database setup.
- **SC-003**: A domain going down is visible on the dashboard within 10 seconds of the first failed check.
- **SC-004**: Dashboard status and uptime figures load in under 2 seconds with 30 days of accumulated history.
- **SC-005**: Restarting the watchdog 5 times in a row causes no setup errors and no loss of previously recorded history.

## Assumptions

- The watchdog runs on the operator's local machine for a single operator; no user accounts or authentication are required, and the dashboard and service are only reachable from localhost.
- The database runs locally in a container on port 5432 with the credentials provided by the user (user `postgres`, password `password`); these are local development credentials and will be read from configuration rather than hard-coded in source.
- "Raw HTTP request" means a plain HTTP GET to `http://<domain>/` without following redirects; any response below 400 (including redirects to HTTPS) counts as up.
- History is retained indefinitely for v1 (about 69,000 records per day across four domains); automatic pruning is out of scope.
- Alerting (email, chat notifications) is out of scope; state changes are only logged and visible on the dashboard.
- Adding/removing domains through the dashboard is out of scope for v1; the four domains are seeded by the migration.
- Checks during a database outage may be lost; buffering is out of scope.
