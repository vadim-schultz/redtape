import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { expect, it } from "vitest";

import { useApiQuery } from "./useApiQuery";

function renderApiQuery(queryFn: () => Promise<string>) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
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
