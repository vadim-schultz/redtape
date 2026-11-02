import {
  QueryClient,
  QueryClientProvider,
  skipToken,
} from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { expect, it, vi } from "vitest";

import { useApiQuery } from "./useApiQuery";

function queryClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function wrapperFor(client: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
  };
}

function renderApiQuery(queryFn: () => Promise<string>) {
  const wrapper = wrapperFor(queryClient());
  return renderHook(() => useApiQuery(["test"], queryFn), { wrapper });
}

it("useApiQuery · exposes the resolved data", async () => {
  const { result } = renderApiQuery(async () => "ok");
  await waitFor(() => expect(result.current.data).toBe("ok"));
});

it("useApiQuery · exposes the rejection as error", async () => {
  const { result } = renderApiQuery(async () => {
    throw new Error("boom");
  });
  await waitFor(() => expect(result.current.error?.message).toBe("boom"));
  expect(result.current.data).toBeUndefined();
});

it("useApiQuery · a skipToken query function never runs", async () => {
  const client = queryClient();
  const spy = vi.fn(async () => "unused");
  const { result, rerender } = renderHook(
    ({ fn }: { fn: typeof skipToken | typeof spy }) =>
      useApiQuery(["skip-token-test"], fn),
    { wrapper: wrapperFor(client), initialProps: { fn: skipToken } },
  );

  await new Promise((resolve) => setTimeout(resolve, 10));
  expect(spy).not.toHaveBeenCalled();
  expect(result.current.isPending).toBe(true);

  rerender({ fn: spy });
  await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
});
