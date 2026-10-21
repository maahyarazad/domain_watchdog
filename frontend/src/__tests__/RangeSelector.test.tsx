import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { RangeSelector } from '../components/RangeSelector'

describe('RangeSelector', () => {
  it('marks the active range and reports changes', () => {
    const onChange = vi.fn()
    render(<RangeSelector value="24h" onChange={onChange} />)
    expect(screen.getAllByRole('button')).toHaveLength(3)
    expect(screen.getByRole('button', { name: 'Last 24 hours' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'Last hour' })).toHaveAttribute('aria-pressed', 'false')
    fireEvent.click(screen.getByRole('button', { name: 'Last hour' }))
    fireEvent.click(screen.getByRole('button', { name: 'Last 7 days' }))
    expect(onChange.mock.calls).toEqual([['1h'], ['7d']])
  })
})
