import { fetchChart, type ChartRange } from '../api/client'
import { usePolling } from '../hooks/usePolling'
import { UptimeChart } from './UptimeChart'

export const CHART_POLL_MS = 15000

function DomainChart({ hostname, range }: { hostname: string; range: ChartRange }) {
  const chart = usePolling((signal) => fetchChart(hostname, range, signal), CHART_POLL_MS, [hostname, range])
  const loading = chart.data === null || chart.data.hostname !== hostname
  // After a range switch the previous chart stays on screen, dimmed, until the new one arrives.
  const stale = chart.error !== null || (chart.data !== null && chart.data.range !== range)

  return (
    <div className="chart-card">
      {loading ? (
        <p className="chart-empty">{chart.error ? hostname : 'Loading…'}</p>
      ) : (
        <UptimeChart data={chart.data!} stale={stale} />
      )}
      {chart.error && (
        <p className="chart-error" role="status">
          Cannot reach watchdog service
          {chart.lastUpdated ? ` — chart from ${chart.lastUpdated.toLocaleTimeString()}` : ''}
        </p>
      )}
    </div>
  )
}

export function ChartGrid({ hostnames, range }: { hostnames: string[]; range: ChartRange }) {
  return (
    <div className="chart-grid">
      {hostnames.map((h) => (
        <DomainChart key={h} hostname={h} range={range} />
      ))}
    </div>
  )
}
