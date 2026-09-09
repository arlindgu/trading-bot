import { useEffect, useRef, useState } from "react"

/**
 * `resetKey` forces an immediate refetch (and clears stale data) when it
 * changes -- e.g. pass the selected account so switching accounts doesn't
 * wait up to `intervalMs` to show the new one's data.
 */
export function usePolling<T>(fetcher: () => Promise<T>, intervalMs: number, resetKey: unknown = null) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  useEffect(() => {
    setData(null)
    let cancelled = false

    async function load() {
      try {
        const result = await fetcherRef.current()
        if (!cancelled) {
          setData(result)
          setError(null)
        }
      } catch (e) {
        if (!cancelled) setError(e as Error)
      }
    }

    load()
    const id = setInterval(load, intervalMs)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [intervalMs, resetKey])

  return { data, error }
}
