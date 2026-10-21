import { describe, expect, it } from 'vitest'
import type { ChartPoint } from '../api/client'
import { bandRect, buildLineSegments, formatDuration, niceMax, scaleX, scaleY } from '../lib/chartGeometry'

const pt = (t: string, avg: number | null): ChartPoint => ({ t, avg_ms: avg, max_ms: avg, checks: 1, down: avg === null ? 1 : 0 })

describe('chartGeometry', () => {
  it('scales x and y', () => {
    expect(scaleX(50, 0, 100, 200)).toBe(100)
    expect(scaleX(5, 5, 5, 200)).toBe(0)
    expect(scaleY(0, 200, 100)).toBe(100)
    expect(scaleY(200, 200, 100)).toBe(0)
  })

  it('rounds the y max to 1/2/5 x 10^n', () => {
    expect(niceMax(0)).toBe(100)
    expect(niceMax(42)).toBe(50)
    expect(niceMax(51)).toBe(100)
    expect(niceMax(130)).toBe(200)
    expect(niceMax(1000)).toBe(1000)
    expect(niceMax(3100)).toBe(5000)
  })

  it('returns no segments for empty input', () => {
    expect(buildLineSegments([], [], 30)).toEqual([])
  })

  it('keeps contiguous points in one segment', () => {
    const segs = buildLineSegments([pt('2026-10-21T10:00:00Z', 10), pt('2026-10-21T10:00:30Z', 20)], [], 30)
    expect(segs).toHaveLength(1)
    expect(segs[0].map((s) => s.ms)).toEqual([10, 20])
  })

  it('splits at buckets with no up checks', () => {
    const segs = buildLineSegments(
      [pt('2026-10-21T10:00:00Z', 10), pt('2026-10-21T10:00:30Z', null), pt('2026-10-21T10:01:00Z', 30)],
      [],
      30,
    )
    expect(segs.map((s) => s.map((p) => p.ms))).toEqual([[10], [30]])
  })

  it('splits at missing buckets and at gaps crossing a boundary', () => {
    const missing = buildLineSegments([pt('2026-10-21T10:00:00Z', 10), pt('2026-10-21T10:05:00Z', 20)], [], 30)
    expect(missing).toHaveLength(2)
    const gap = buildLineSegments(
      [pt('2026-10-21T10:00:00Z', 10), pt('2026-10-21T10:00:30Z', 20)],
      [{ started_at: '2026-10-21T10:00:20Z', ended_at: '2026-10-21T10:00:40Z' }],
      30,
    )
    expect(gap).toHaveLength(2)
  })

  it('gives bands a minimum visible width and keeps them inside the plot', () => {
    const one = { started_at: '2026-10-21T10:30:00Z', ended_at: '2026-10-21T10:30:00Z' }
    const r = bandRect(one, Date.parse('2026-10-21T10:00:00Z'), Date.parse('2026-10-21T11:00:00Z'), 600)
    expect(r.width).toBe(3)
    expect(r.x).toBeCloseTo(298.5)
    const edge = bandRect({ started_at: '2026-10-21T11:00:00Z', ended_at: '2026-10-21T11:00:00Z' }, Date.parse('2026-10-21T10:00:00Z'), Date.parse('2026-10-21T11:00:00Z'), 600)
    expect(edge.x + edge.width).toBeLessThanOrEqual(600)
    const long = bandRect({ started_at: '2026-10-21T10:15:00Z', ended_at: '2026-10-21T10:30:00Z' }, Date.parse('2026-10-21T10:00:00Z'), Date.parse('2026-10-21T11:00:00Z'), 600)
    expect(long).toEqual({ x: 150, width: 150 })
  })

  it('formats durations', () => {
    expect(formatDuration(0)).toBe('0s')
    expect(formatDuration(45)).toBe('45s')
    expect(formatDuration(200)).toBe('3m 20s')
    expect(formatDuration(7500)).toBe('2h 5m')
    expect(formatDuration(97200)).toBe('1d 3h')
  })
})
