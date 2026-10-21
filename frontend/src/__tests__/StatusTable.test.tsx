import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { DomainStatus } from '../api/client'
import { StatusTable } from '../components/StatusTable'

const base: DomainStatus = {
  hostname: 'a.com', display_name: 'A', is_up: true, last_checked_at: '2026-10-21T10:00:00Z',
  status_code: 200, response_time_ms: 42, error: null, uptime_1h: 100, uptime_24h: 99.5, checks_24h: 10,
}

describe('StatusTable', () => {
  it('renders up and down', () => {
    render(<StatusTable domains={[base, { ...base, hostname: 'b.com', is_up: false, error: 'timeout' }]} />)
    expect(screen.getByText('UP')).toBeInTheDocument()
    expect(screen.getByText(/DOWN \(timeout\)/)).toBeInTheDocument()
    expect(screen.getAllByText('42 ms')).toHaveLength(2)
  })
  it('renders no data', () => {
    render(<StatusTable domains={[{ ...base, is_up: null, uptime_1h: null, uptime_24h: null, response_time_ms: null, last_checked_at: null }]} />)
    expect(screen.getByText('no data yet')).toBeInTheDocument()
    expect(screen.getAllByText('no data')).toHaveLength(2)
  })
  it('renders error banner with last updated', () => {
    render(<StatusTable domains={[base]} error={new Error('x')} lastUpdated={new Date()} />)
    expect(screen.getByRole('alert')).toHaveTextContent(/cannot reach watchdog service/i)
  })
})
