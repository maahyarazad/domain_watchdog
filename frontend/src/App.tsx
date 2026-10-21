import { useState } from 'react'
import { fetchChecks, fetchStatus, type ChartRange } from './api/client'
import { ChartGrid } from './components/ChartGrid'
import { RangeSelector } from './components/RangeSelector'
import { CheckHistory } from './components/CheckHistory'
import { StatusTable } from './components/StatusTable'
import { usePolling } from './hooks/usePolling'

export default function App() {
  const [selected, setSelected] = useState<string | null>(null)
  const [range, setRange] = useState<ChartRange>('24h')
  const status = usePolling(fetchStatus, 5000)
  const history = usePolling(
    (signal) => (selected ? fetchChecks(selected, 100, signal) : Promise.resolve(null)),
    5000,
  )
  const showHistory = selected && history.data && history.data.hostname === selected

  return (
    <main>
      <h1>Domain Watchdog</h1>
      {!status.data && !status.error && <p>Loading…</p>}
      {(status.data || status.error) && (
        <StatusTable
          domains={status.data?.domains ?? []}
          selected={selected}
          onSelect={setSelected}
          error={status.error}
          lastUpdated={status.lastUpdated}
        />
      )}
      {status.data && status.data.domains.length > 0 && (
        <section>
          <div className="chart-header">
            <h2>Response time</h2>
            <RangeSelector value={range} onChange={setRange} />
          </div>
          <ChartGrid hostnames={status.data.domains.map((d) => d.hostname)} range={range} />
        </section>
      )}
      {showHistory && <CheckHistory hostname={selected} checks={history.data!.checks} />}
    </main>
  )
}
