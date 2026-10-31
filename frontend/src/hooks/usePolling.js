import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Calls `fetcher` immediately and then every `intervalMs` (paused while the tab is hidden).
 * Returns { data, error, loading, refresh }.
 */
export default function usePolling(fetcher, intervalMs, deps = []) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const refresh = useCallback(async () => {
    try {
      const result = await fetcherRef.current();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    refresh();
    if (!intervalMs) return undefined;
    const id = setInterval(() => {
      if (document.visibilityState === "visible") refresh();
    }, intervalMs);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs, refresh, ...deps]);

  return { data, error, loading, refresh };
}
