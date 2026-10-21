import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'

const status = {
  generated_at: '2026-10-21T10:00:00Z',
  interval_seconds: 5,
  domains: ['a.com', 'b.com', 'c.com', 'd.com'].map((hostname) => ({
    hostname, display_name: hostname, is_up: true, last_checked_at: '2026-10-21T10:00:00Z',
    status_code: 200, response_time_ms: 10, error: null, uptime_1h: 100, uptime_24h: 100, checks_24h: 10,
  })),
}

const chart = (hostname: string, range: string) => ({
  hostname, range, from: '2026-10-21T09:00:00Z', to: '2026-10-21T10:00:00Z', bucket_seconds: 30,
  points: [{ t: '2026-10-21T09:30:00Z', avg_ms: 10, max_ms: 10, checks: 6, down: 0 }],
  downtime: [], gaps: [], summary: { down_periods: 0, total_downtime_seconds: 0, checks: 6 },
})

let failCharts = false
const fetchMock = vi.fn(async (url: string) => {
  const json = (b: unknown) => ({ ok: true, status: 200, json: async () => b })
  if (url.includes('/chart')) {
    if (failCharts) throw new Error('network down')
    const m = /domains\/([^/]+)\/chart\?range=(\w+)/.exec(url)!
    return json(chart(m[1], m[2]))
  }
  if (url.includes('/status')) return json(status)
  return json({ hostname: 'x', checks: [] })
})

const chartCalls = () => fetchMock.mock.calls.map((c) => c[0] as string).filter((u) => u.includes('/chart'))
const flush = () => act(async () => { await vi.advanceTimersByTimeAsync(0) })

beforeEach(() => {
  vi.useFakeTimers()
  failCharts = false
  fetchMock.mockClear()
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('App charts', () => {
  it('renders four charts on the default 24h range', async () => {
    render(<App />)
    await flush()
    await flush()
    expect(screen.getAllByRole('img')).toHaveLength(4)
    expect(chartCalls().sort()).toEqual(['a.com', 'b.com', 'c.com', 'd.com'].map((h) => `/api/domains/${h}/chart?range=24h`))
  })

  it('requests the new range for all four domains when switched', async () => {
    render(<App />)
    await flush()
    await flush()
    fetchMock.mockClear()
    fireEvent.click(screen.getByRole('button', { name: 'Last hour' }))
    await flush()
    expect(chartCalls().sort()).toEqual(['a.com', 'b.com', 'c.com', 'd.com'].map((h) => `/api/domains/${h}/chart?range=1h`))
  })

  it('refreshes charts every 15 seconds', async () => {
    render(<App />)
    await flush()
    await flush()
    fetchMock.mockClear()
    await act(async () => { await vi.advanceTimersByTimeAsync(15000) })
    expect(chartCalls()).toHaveLength(4)
  })

  it('keeps existing charts and shows the unreachable message when a refresh fails', async () => {
    render(<App />)
    await flush()
    await flush()
    failCharts = true
    await act(async () => { await vi.advanceTimersByTimeAsync(15000) })
    expect(screen.getAllByRole('img')).toHaveLength(4)
    expect(screen.getAllByText(/cannot reach watchdog service/i).length).toBeGreaterThan(0)
  })
})
