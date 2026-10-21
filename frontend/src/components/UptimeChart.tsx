import { useId, useState } from 'react'
import type { ChartResponse } from '../api/client'
import { bandRect, buildLineSegments, formatDuration, niceMax, scaleX, scaleY } from '../lib/chartGeometry'

const W = 600
const H = 160
const M = { left: 48, right: 12, top: 8, bottom: 22 }
const PW = W - M.left - M.right
const PH = H - M.top - M.bottom

interface Props {
  data: ChartResponse
  stale?: boolean
}

const when = (iso: string) => new Date(iso).toLocaleString()
const tickLabel = (ms: number, range: string) =>
  new Date(ms).toLocaleString([], range === '7d' ? { month: 'short', day: 'numeric' } : { hour: '2-digit', minute: '2-digit' })

export function UptimeChart({ data, stale = false }: Props) {
  const patternId = useId()
  const [tip, setTip] = useState<string | null>(null)
  const from = Date.parse(data.from)
  const to = Date.parse(data.to)
  const maxMs = Math.max(0, ...data.points.map((p) => p.max_ms ?? 0))
  const yMax = niceMax(maxMs)
  const segments = buildLineSegments(data.points, data.gaps, data.bucket_seconds)
  const { summary } = data
  const xTicks = [0, 0.25, 0.5, 0.75, 1].map((f) => from + f * (to - from))

  return (
    <figure className={`chart${stale ? ' stale' : ''}`}>
      <figcaption>
        <strong>{data.hostname}</strong>
        <span className="chart-summary">
          {summary.down_periods === 0
            ? 'No downtime'
            : `${summary.down_periods} down period${summary.down_periods === 1 ? '' : 's'}, ${formatDuration(summary.total_downtime_seconds)} total`}
        </span>
      </figcaption>
      {data.points.length === 0 ? (
        <p className="chart-empty">No data for this period</p>
      ) : (
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Response time for ${data.hostname}`}>
          <defs>
            <pattern id={patternId} width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <rect width="6" height="6" className="hatch-bg" />
              <line x1="0" y1="0" x2="0" y2="6" className="hatch-line" strokeWidth="3" />
            </pattern>
          </defs>
          <g transform={`translate(${M.left},${M.top})`}>
            {[0, 0.5, 1].map((f) => (
              <g key={f}>
                <line x1="0" x2={PW} y1={PH - f * PH} y2={PH - f * PH} className="grid" />
                <text x="-6" y={PH - f * PH + 4} textAnchor="end" className="axis">{`${Math.round(f * yMax)} ms`}</text>
              </g>
            ))}
            {xTicks.map((t, i) => (
              <text key={t} x={scaleX(t, from, to, PW)} y={PH + 16} textAnchor={i === 0 ? 'start' : i === 4 ? 'end' : 'middle'} className="axis">
                {tickLabel(t, data.range)}
              </text>
            ))}
            {data.gaps.map((g) => {
              const x1 = scaleX(Date.parse(g.started_at), from, to, PW)
              const x2 = scaleX(Date.parse(g.ended_at), from, to, PW)
              return <rect key={g.started_at} x={x1} y={0} width={Math.max(x2 - x1, 1)} height={PH} className="gap" data-testid="gap" />
            })}
            {data.downtime.map((d) => {
              const r = bandRect(d, from, to, PW)
              const label = `Down ${when(d.started_at)} to ${when(d.ended_at)} (${formatDuration((Date.parse(d.ended_at) - Date.parse(d.started_at)) / 1000)}), ${d.failed_checks} failed check${d.failed_checks === 1 ? '' : 's'}${d.errors.length ? `, ${d.errors.join(', ')}` : ''}${d.ongoing ? ', ongoing' : ''}`
              return (
                <rect
                  key={d.started_at}
                  x={r.x}
                  y={0}
                  width={r.width}
                  height={PH}
                  fill={`url(#${patternId})`}
                  className="downtime"
                  data-testid="downtime"
                  tabIndex={0}
                  aria-label={label}
                  onMouseEnter={() => setTip(label)}
                  onFocus={() => setTip(label)}
                  onMouseLeave={() => setTip(null)}
                  onBlur={() => setTip(null)}
                />
              )
            })}
            {segments.map((seg, i) => (
              <polyline
                key={i}
                className="line"
                fill="none"
                points={seg.map((s) => `${scaleX(s.t, from, to, PW)},${scaleY(s.ms, yMax, PH)}`).join(' ')}
              />
            ))}
            {data.points.map((p) => {
              if (p.avg_ms === null) return null
              const label = `${when(p.t)}: ${p.down ? `${p.down} of ${p.checks} checks failed, ` : 'up, '}avg response ${Math.round(p.avg_ms)} ms`
              return (
                <circle
                  key={p.t}
                  cx={scaleX(Date.parse(p.t), from, to, PW)}
                  cy={scaleY(p.avg_ms, yMax, PH)}
                  r="3"
                  className="dot"
                  data-testid="point"
                  tabIndex={0}
                  aria-label={label}
                  onMouseEnter={() => setTip(label)}
                  onFocus={() => setTip(label)}
                  onMouseLeave={() => setTip(null)}
                  onBlur={() => setTip(null)}
                />
              )
            })}
          </g>
        </svg>
      )}
      <div className="chart-tip" role="status">{tip ?? ' '}</div>
    </figure>
  )
}
