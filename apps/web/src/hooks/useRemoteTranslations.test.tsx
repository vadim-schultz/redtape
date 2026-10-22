import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { useRemoteTranslations } from "./useRemoteTranslations";

function stubFetch(response: Promise<Response>) {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => response),
  );
}

afterEach(() => vi.unstubAllGlobals());

it("useRemoteTranslations · exposes the fetched bundle once loaded", async () => {
  stubFetch(
    Promise.resolve(new Response(JSON.stringify({ translations: { a: "A" } }))),
  );

  const { result } = renderHook(() => useRemoteTranslations("en"));

  expect(result.current.isLoading).toBe(true);
  await waitFor(() => expect(result.current.isLoading).toBe(false));
  expect(result.current.remote).toEqual({ a: "A" });
});

it("useRemoteTranslations · falls back to an empty bundle when the request fails", async () => {
  stubFetch(Promise.reject(new Error("offline")));

  const { result } = renderHook(() => useRemoteTranslations("en"));

  await waitFor(() => expect(result.current.isLoading).toBe(false));
  expect(result.current.remote).toEqual({});
});
