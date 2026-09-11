"use client";

import { useCallback, useEffect, useEffectEvent, useState } from "react";

interface QueryState<T> {
  data: T | null;
  error: Error | null;
  isLoading: boolean;
  retry: () => void;
}

export function useApiQuery<T>(
  queryKey: string,
  loader: (signal: AbortSignal) => Promise<T>,
  enabled = true,
): QueryState<T> {
  const [attempt, setAttempt] = useState(0);
  const activeKey = enabled ? `${queryKey}:${attempt}` : "";
  const [state, setState] = useState<{
    key: string;
    data: T | null;
    error: Error | null;
  }>({
    key: "",
    data: null,
    error: null,
  });
  const runLoader = useEffectEvent(loader);

  useEffect(() => {
    if (!enabled) return;

    const controller = new AbortController();
    runLoader(controller.signal).then(
      (data) => setState({ key: activeKey, data, error: null }),
      (error: unknown) => {
        if (controller.signal.aborted) return;
        setState({
          key: activeKey,
          data: null,
          error: error instanceof Error ? error : new Error(String(error)),
        });
      },
    );

    return () => controller.abort();
  }, [activeKey, enabled]);

  const retry = useCallback(() => setAttempt((current) => current + 1), []);
  const settled = enabled && state.key === activeKey;

  return {
    data: settled ? state.data : null,
    error: settled ? state.error : null,
    isLoading: enabled && !settled,
    retry,
  };
}
