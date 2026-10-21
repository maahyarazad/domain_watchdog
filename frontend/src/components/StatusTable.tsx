import type { DomainStatus } from '../api/client'

interface Props {
  domains: DomainStatus[]
  selected?: string | null
  onSelect?: (hostname: string) => void
  error?: Error | null
  lastUpdated?: Date | null
}

const pct = (v: number | null) => (v === null ? 'no data' : `${v.toFixed(2)}%`)

export function StatusTable({ domains, selected, onSelect, error, lastUpdated }: Props) {
  return (
    <section>
      {error && (
        <div role="alert" className="banner">
          Cannot reach watchdog service
          {lastUpdated ? ` — showing data from ${lastUpdated.toLocaleTimeString()}` : ''}
        </div>
      )}
      <table>
        <thead>
          <tr>
            <th>Domain</th>
            <th>Status</th>
            <th>Last check</th>
            <th>Latency</th>
            <th>Uptime 1 h</th>
            <th>Uptime 24 h</th>
          </tr>
        </thead>
        <tbody>
          {domains.map((d) => (
            <tr
              key={d.hostname}
              className={d.hostname === selected ? 'selected' : ''}
              onClick={() => onSelect?.(d.hostname)}
            >
              <td>{d.hostname}</td>
              <td>
                {d.is_up === null ? (
                  <span className="badge unknown">no data yet</span>
                ) : d.is_up ? (
                  <span className="badge up">UP</span>
                ) : (
                  <span className="badge down">DOWN{d.error ? ` (${d.error})` : ''}</span>
                )}
              </td>
              <td>{d.last_checked_at ? new Date(d.last_checked_at).toLocaleTimeString() : '—'}</td>
              <td>{d.response_time_ms === null ? '—' : `${d.response_time_ms} ms`}</td>
              <td>{pct(d.uptime_1h)}</td>
              <td>{pct(d.uptime_24h)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
