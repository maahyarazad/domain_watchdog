import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { CheckHistory } from '../components/CheckHistory'

describe('CheckHistory', () => {
  it('lists checks in given order and marks failures', () => {
    const { container } = render(
      <CheckHistory
        hostname="a.com"
        checks={[
          { checked_at: '2026-10-21T10:00:05Z', is_up: false, status_code: null, response_time_ms: null, error: 'timeout' },
          { checked_at: '2026-10-21T10:00:00Z', is_up: true, status_code: 200, response_time_ms: 30, error: null },
        ]}
      />,
    )
    const rows = container.querySelectorAll('tbody tr')
    expect(rows[0]).toHaveClass('check-down')
    expect(rows[1]).toHaveClass('check-up')
    expect(screen.getByText('timeout')).toBeInTheDocument()
    expect(screen.getByText('30 ms')).toBeInTheDocument()
  })
})
