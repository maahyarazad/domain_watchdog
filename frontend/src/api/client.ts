export async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(path, { signal })
  if (!res.ok) throw new Error(`${path} failed with HTTP ${res.status}`)
  return (await res.json()) as T
}

export interface DomainStatus {
  hostname: string
  display_name: string
  is_up: boolean | null
  last_checked_at: string | null
  status_code: number | null
  response_time_ms: number | null
  error: string | null
  uptime_1h: number | null
  uptime_24h: number | null
  checks_24h: number
}

export interface StatusResponse {
  generated_at: string
  interval_seconds: number
  domains: DomainStatus[]
}

export interface CheckResult {
  checked_at: string
  is_up: boolean
  status_code: number | null
  response_time_ms: number | null
  error: string | null
}

export interface ChecksResponse {
  hostname: string
  checks: CheckResult[]
}

export const fetchStatus = (signal?: AbortSignal) =>
  getJson<StatusResponse>('/api/domains/status', signal)

export const fetchChecks = (hostname: string, limit = 100, signal?: AbortSignal) =>
  getJson<ChecksResponse>(`/api/domains/${encodeURIComponent(hostname)}/checks?limit=${limit}`, signal)

export type ChartRange = '1h' | '24h' | '7d'

export interface ChartPoint {
  t: string
  avg_ms: number | null
  max_ms: number | null
  checks: number
  down: number
}

export interface DowntimePeriod {
  started_at: string
  ended_at: string
  failed_checks: number
  errors: string[]
  ongoing: boolean
}

export interface Gap {
  started_at: string
  ended_at: string
}

export interface ChartSummary {
  down_periods: number
  total_downtime_seconds: number
  checks: number
}

export interface ChartResponse {
  hostname: string
  range: ChartRange
  from: string
  to: string
  bucket_seconds: number
  points: ChartPoint[]
  downtime: DowntimePeriod[]
  gaps: Gap[]
  summary: ChartSummary
}

export const fetchChart = (hostname: string, range: ChartRange, signal?: AbortSignal) =>
  getJson<ChartResponse>(`/api/domains/${encodeURIComponent(hostname)}/chart?range=${range}`, signal)
