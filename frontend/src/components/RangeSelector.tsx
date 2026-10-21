import type { ChartRange } from '../api/client'

const OPTIONS: { value: ChartRange; label: string }[] = [
  { value: '1h', label: 'Last hour' },
  { value: '24h', label: 'Last 24 hours' },
  { value: '7d', label: 'Last 7 days' },
]

interface Props {
  value: ChartRange
  onChange: (range: ChartRange) => void
}

export function RangeSelector({ value, onChange }: Props) {
  return (
    <div className="range-selector" role="group" aria-label="Chart time range">
      {OPTIONS.map((o) => (
        <button key={o.value} type="button" aria-pressed={o.value === value} onClick={() => onChange(o.value)}>
          {o.label}
        </button>
      ))}
    </div>
  )
}
