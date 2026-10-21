# Feature Specification: Uptime Line Charts

**Feature Branch**: `002-uptime-line-charts`

**Created**: 2026-10-21

**Status**: Draft

**Input**: User description: "Line charts of each monitored domain built from the stored check data in the database (response time and up/down over time) on the dashboard, so the operator can check downtime periods."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See a domain's response time and downtime on a line chart (Priority: P1)

As the site operator, I open the dashboard and see, for each of the four monitored domains, a line chart of its stored checks over a chosen time range. The line shows response time over time, and periods when the domain was down are clearly marked, so I can see at a glance when and for how long each domain was unavailable.

**Why this priority**: Spotting downtime periods is the whole purpose of the request; a per-domain chart with marked downtime delivers it on its own.

**Independent Test**: With history present (including at least one period of failed checks), open the dashboard, pick a time range covering that period, and verify each domain shows a line chart where the failed period is visibly marked and its start and end times match the stored records.

**Acceptance Scenarios**:

1. **Given** stored checks exist for a domain, **When** the operator opens the dashboard, **Then** that domain shows a line chart of response time against time for the default range.
2. **Given** a domain had consecutive failed checks, **When** the operator views its chart, **Then** the failed period is visibly distinct (e.g., a highlighted band or gap) and covers the time from its first to its last failed check.
3. **Given** the operator hovers over or selects a point on the chart, **When** the point is a check, **Then** its time, outcome, response time (if any), and error reason (if any) are shown.
4. **Given** a domain has no checks in the chosen range, **When** the chart is displayed, **Then** it shows "no data for this period" instead of an empty or misleading chart.

---

### User Story 2 - Choose the time range to inspect (Priority: P2)

As the site operator, I switch between preset ranges (last hour, last 24 hours, last 7 days) so I can look at both a recent incident and longer-term patterns.

**Why this priority**: Downtime usually happened some time ago; choosing the range makes the charts useful beyond the last few minutes.

**Independent Test**: Select each range and verify every chart's time axis and plotted data match that range, with the same range applied to all four domains.

**Acceptance Scenarios**:

1. **Given** the dashboard is open, **When** the operator selects a range, **Then** all four charts update to cover exactly that range.
2. **Given** a long range with many stored checks (e.g., 7 days), **When** the charts load, **Then** they remain readable and any downtime period still shows, even if shorter than one visible pixel of the original data.

---

### User Story 3 - Charts stay current (Priority: P3)

As the site operator, I leave the dashboard open and the charts extend with new checks, and a new outage appears without reloading the page.

**Why this priority**: Nice for live monitoring, but the historical view already satisfies the core need.

**Independent Test**: Keep the dashboard open on the last-hour range while a domain starts failing, and verify the failure appears on its chart within 15 seconds without a manual reload.

**Acceptance Scenarios**:

1. **Given** the dashboard is open on a recent range, **When** new checks are stored, **Then** the charts include them within 15 seconds.
2. **Given** the watchdog service is unreachable, **When** a refresh happens, **Then** the dashboard shows the existing "cannot reach watchdog service" message rather than presenting stale charts as current.

---

### Edge Cases

- A domain has a gap in checks (watchdog was stopped): the gap is shown as missing data, not as downtime or as a continuous line.
- Failed checks have no response time: they must still appear as downtime on the chart rather than being dropped or plotted as zero.
- A single isolated failed check: still marked as downtime, even though it is brief.
- Very different response times across domains: each domain has its own chart scale so one slow domain does not flatten the others.
- Fresh start with no data for any domain: all charts show "no data yet".

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Dashboard MUST show one line chart per monitored domain (four total), built from the stored check results, plotting response time against check time.
- **FR-002**: Each chart MUST visibly mark periods when the domain was down, from its first to its last consecutive failed check, distinguishable from up periods without relying on color alone.
- **FR-003**: Failed checks that have no response time MUST still be represented as downtime and MUST NOT be plotted as a zero response time.
- **FR-004**: Dashboard MUST let the operator choose a time range from: last hour, last 24 hours, last 7 days, applied to all four charts; the default is last 24 hours.
- **FR-005**: System MUST provide chart data for a domain and range such that the full range is covered regardless of how many checks are stored, without dropping downtime periods when data is condensed for display.
- **FR-006**: Dashboard MUST show, for a selected point or period on a chart, the time, outcome, response time (if any), and error reason (if any).
- **FR-007**: Dashboard MUST show a "no data" message for a chart whose range contains no checks, and distinguish gaps in checking from downtime.
- **FR-008**: Dashboard MUST refresh the charts automatically at least every 15 seconds and MUST show the existing "cannot reach watchdog service" error state when the service is unreachable.
- **FR-009**: Each chart MUST show the domain name and the number of down periods and total downtime within the selected range.

### Key Entities

- **Check Result**: (existing) one availability probe of a domain with time, outcome, status code, response time, and error reason.
- **Chart Series** (derived, not stored): For one domain and time range, the ordered response-time points plus the list of downtime periods.
- **Downtime Period** (derived, not stored): A start time, end time, and the error reason(s) of a run of consecutive failed checks for one domain.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The operator can identify when each domain was last down, and for how long, within 10 seconds of opening the dashboard.
- **SC-002**: Every period of consecutive failed checks in the selected range appears on the chart, and its start and end times match the stored records to within one check interval.
- **SC-003**: All four charts load in under 3 seconds for any of the three ranges with 7 days of accumulated history.
- **SC-004**: A new outage appears on the charts within 15 seconds of its first failed check without reloading the page.
- **SC-005**: Switching the time range updates all four charts in under 2 seconds.

## Assumptions

- This extends the existing dashboard from feature 001; monitoring, storage, and check intervals are unchanged and no new data is collected.
- Single local operator with no authentication, as in 001.
- Ranges are limited to last hour, 24 hours, and 7 days; custom date pickers are out of scope.
- A downtime period is a run of consecutive failed checks; checks are 5 seconds apart, so a gap longer than a few missed intervals is treated as missing data, not downtime.
- Exporting charts, alerting, and comparing domains on a single shared chart are out of scope.
