import type { CheckResult } from '../api/client'

export function CheckHistory({ hostname, checks }: { hostname: string; checks: CheckResult[] }) {
  return (
    <section>
      <h2>Recent checks — {hostname}</h2>
      <table>
        <thead>
          <tr><th>Time</th><th>Outcome</th><th>Status</th><th>Latency</th><th>Error</th></tr>
        </thead>
        <tbody>
          {checks.map((c) => (
            <tr key={c.checked_at} className={c.is_up ? 'check-up' : 'check-down'}>
              <td>{new Date(c.checked_at).toLocaleTimeString()}</td>
              <td>{c.is_up ? 'UP' : 'DOWN'}</td>
              <td>{c.status_code ?? '—'}</td>
              <td>{c.response_time_ms === null ? '—' : `${c.response_time_ms} ms`}</td>
              <td>{c.error ?? ''}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
