"use client";

import { ErrorState } from "@/components/ui/data-state";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return <ErrorState error={error} onRetry={reset} />;
}

