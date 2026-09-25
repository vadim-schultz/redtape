import { QueryClient } from "@tanstack/react-query";

import { retryDelay, shouldRetry } from "./retryPolicy";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 15_000,
      gcTime: 5 * 60_000,
      refetchOnWindowFocus: false,
      retry: shouldRetry,
      retryDelay,
    },
  },
});
