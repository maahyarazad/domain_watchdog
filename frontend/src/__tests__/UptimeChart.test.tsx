import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { ChartResponse } from '../api/client'
import { UptimeChart } from '../components/UptimeChart'

const base: ChartResponse = {
  hostname: 'a.com',
  range: '1h',
  from: '2026-10-21T10:00:00Z',
  to: '2026-10-21T11:00:00Z',
  bucket_seconds: 30,
  points: [
    { t: '2026-10-21T10:10:00Z', avg_ms: 42, max_ms: 60, checks: 6, down: 0 },
    { t: '2026-10-21T10:10:30Z', avg_ms: 50, max_ms: 70, checks: 6, down: 1 },
  ],
  downtime: [
    { started_at: '2026-10-21T10:20:00Z', ended_at: '2026-10-21T10:20:45Z', failed_checks: 10, errors: ['timeout'], ongoing: false },
    { started_at: '2026-10-21T10:40:00Z', ended_at: '2026-10-21T10:40:00Z', failed_checks: 1, errors: ['dns_error'], ongoing: false },
  ],
  gaps: [{ started_at: '2026-10-21T10:30:00Z', ended_at: '2026-10-21T10:35:00Z' }],
  summary: { down_periods: 2, total_downtime_seconds: 55, checks: 12 },
}

describe('UptimeChart', () => {
  it('shows the domain and downtime summary', () => {
    render(<UptimeChart data={base} />)
    expect(screen.getByText('a.com')).toBeInTheDocument()
    expect(screen.getByText('2 down periods, 55s total')).toBeInTheDocument()
  })

  it('draws one hatched band per downtime period and one gap marker', () => {
    render(<UptimeChart data={base} />)
    const bands = screen.getAllByTestId('downtime')
    expect(bands).toHaveLength(2)
    bands.forEach((b) => expect(b.getAttribute('fill')).toMatch(/^url\(#/))
    expect(screen.getAllByTestId('gap')).toHaveLength(1)
  })

  it('says no downtime when there is none', () => {
    render(<UptimeChart data={{ ...base, downtime: [], summary: { ...base.summary, down_periods: 0, total_downtime_seconds: 0 } }} />)
    expect(screen.getByText('No downtime')).toBeInTheDocument()
  })

  it('shows "no data" when the range has no points', () => {
    render(<UptimeChart data={{ ...base, points: [], downtime: [], gaps: [] }} />)
    expect(screen.getByText(/no data for this period/i)).toBeInTheDocument()
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
  })

  it('shows point details on hover and band details on focus', () => {
    render(<UptimeChart data={base} />)
    fireEvent.mouseEnter(screen.getAllByTestId('point')[1])
    expect(screen.getByRole('status')).toHaveTextContent(/1 of 6 checks failed, avg response 50 ms/)
    fireEvent.focus(screen.getAllByTestId('downtime')[0])
    expect(screen.getByRole('status')).toHaveTextContent(/10 failed checks, timeout/)
    fireEvent.mouseLeave(screen.getAllByTestId('point')[0])
  })

  it('never plots a point for buckets with no up checks', () => {
    const data = { ...base, points: [{ t: '2026-10-21T10:20:00Z', avg_ms: null, max_ms: null, checks: 6, down: 6 }] }
    render(<UptimeChart data={data} />)
    expect(screen.queryAllByTestId('point')).toHaveLength(0)
  })
})
