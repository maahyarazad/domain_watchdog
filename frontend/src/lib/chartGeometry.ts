import type { ChartPoint, DowntimePeriod, Gap } from '../api/client'

export interface Segment {
  t: number
  ms: number
}

export const scaleX = (t: number, from: number, to: number, width: number) =>
  to === from ? 0 : ((t - from) / (to - from)) * width

export const scaleY = (ms: number, max: number, height: number) => height - (ms / max) * height

/** Round up to 1, 2 or 5 x 10^n so axis labels are tidy; 100 when there is nothing to scale. */
export function niceMax(maxMs: number): number {
  if (!(maxMs > 0)) return 100
  const pow = 10 ** Math.floor(Math.log10(maxMs))
  for (const m of [1, 2, 5, 10]) if (m * pow >= maxMs) return m * pow
  return 10 * pow
}

/**
 * Split points into drawable line segments. A segment ends at a bucket with no up checks
 * (avg_ms null), at a missing bucket, and where a gap in checking crosses a bucket boundary.
 */
export function buildLineSegments(
  points: ChartPoint[],
  gaps: Gap[],
  bucketSeconds: number,
): Segment[][] {
  const bucketMs = bucketSeconds * 1000
  const gapSpans = gaps.map((g) => [Date.parse(g.started_at), Date.parse(g.ended_at)] as const)
  const segments: Segment[][] = []
  let current: Segment[] = []
  let prevT: number | null = null

  for (const p of points) {
    const t = Date.parse(p.t)
    const broken =
      prevT !== null &&
      (t - prevT > bucketMs * 1.5 || gapSpans.some(([s, e]) => s >= prevT! && s < prevT! + bucketMs && e >= t))
    if (broken && current.length) {
      segments.push(current)
      current = []
    }
    if (p.avg_ms === null) {
      if (current.length) segments.push(current)
      current = []
    } else {
      current.push({ t, ms: p.avg_ms })
    }
    prevT = t
  }
  if (current.length) segments.push(current)
  return segments
}

/** Horizontal extent of a downtime period, widened so a one-check outage stays visible. */
export function bandRect(
  period: Pick<DowntimePeriod, 'started_at' | 'ended_at'>,
  from: number,
  to: number,
  width: number,
  minPx = 3,
): { x: number; width: number } {
  const x1 = scaleX(Date.parse(period.started_at), from, to, width)
  const x2 = scaleX(Date.parse(period.ended_at), from, to, width)
  const w = Math.max(x2 - x1, minPx)
  return { x: Math.min(Math.max(x1 - (w - (x2 - x1)) / 2, 0), width - w), width: w }
}

export function formatDuration(seconds: number): string {
  const s = Math.round(seconds)
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  if (m < 60) return s % 60 ? `${m}m ${s % 60}s` : `${m}m`
  const h = Math.floor(m / 60)
  if (h < 24) return m % 60 ? `${h}h ${m % 60}m` : `${h}h`
  const d = Math.floor(h / 24)
  return h % 24 ? `${d}d ${h % 24}h` : `${d}d`
}
