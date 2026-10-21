import { useEffect, useRef, useState } from 'react'

export interface PollingState<T> {
  data: T | null
  error: Error | null
  lastUpdated: Date | null
}

export function usePolling<T>(
  fn: (signal: AbortSignal) => Promise<T>,
  intervalMs: number,
  // Restart polling (immediate fetch, previous data kept) when any of these change.
  deps: readonly unknown[] = [],
): PollingState<T> {
  const [state, setState] = useState<PollingState<T>>({ data: null, error: null, lastUpdated: null })
  const fnRef = useRef(fn)
  fnRef.current = fn

  useEffect(() => {
    const controller = new AbortController()
    let inFlight = false

    const tick = async () => {
      if (inFlight) return
      inFlight = true
      try {
        const data = await fnRef.current(controller.signal)
        if (!controller.signal.aborted) setState({ data, error: null, lastUpdated: new Date() })
      } catch (e) {
        if (!controller.signal.aborted) {
          setState((prev) => ({ ...prev, error: e instanceof Error ? e : new Error(String(e)) }))
        }
      } finally {
        inFlight = false
      }
    }

    void tick()
    const id = setInterval(tick, intervalMs)
    return () => {
      controller.abort()
      clearInterval(id)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs, ...deps])

  return state
}
