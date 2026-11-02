import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, expect, it, vi } from "vitest";

import { LocaleProvider, useLocale } from "../../../contexts/LocaleContext";
import { AuthProvider } from "../../auth/contexts/AuthContext";
import { createFakeAuthGateway } from "../../auth/services/fakeAuthGateway";
import type { AdminAuth } from "../services/discoveryAdminApi";
import { useAdminQuery } from "./useAdminQuery";

const session = { accessToken: "t", userId: "u", email: "a@example.com" };
const keyFor = (locale: string) => ["admin-query-test", locale] as const;

function wrapperWith(configured: boolean) {
  return function Wrapper({ children }: { children: ReactNode }) {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const gateway = configured
      ? createFakeAuthGateway({ session })
      : createFakeAuthGateway({ configured: false });
    return (
      <QueryClientProvider client={queryClient}>
        <LocaleProvider>
          <AuthProvider gateway={gateway}>{children}</AuthProvider>
        </LocaleProvider>
      </QueryClientProvider>
    );
  };
}

beforeEach(() => window.localStorage.setItem("locale", "en"));

it("useAdminQuery · passes the locale and token to the call", async () => {
  const call = vi.fn(async (auth: AdminAuth) => auth);
  const { result } = renderHook(() => useAdminQuery(keyFor, call), {
    wrapper: wrapperWith(true),
  });

  await waitFor(() =>
    expect(result.current.data).toEqual({ locale: "en", accessToken: "t" }),
  );
});

it("useAdminQuery · re-keys when the locale changes", async () => {
  const call = vi.fn(async (auth: AdminAuth) => auth);
  const { result } = renderHook(
    () => ({ query: useAdminQuery(keyFor, call), locale: useLocale() }),
    { wrapper: wrapperWith(true) },
  );

  await waitFor(() =>
    expect(call).toHaveBeenLastCalledWith({ locale: "en", accessToken: "t" }),
  );
  const callsBeforeChange = call.mock.calls.length;
  act(() => result.current.locale.setLocale("de"));
  await waitFor(() =>
    expect(call).toHaveBeenLastCalledWith({ locale: "de", accessToken: "t" }),
  );
  expect(call.mock.calls.length).toBeGreaterThan(callsBeforeChange);
});

it("useAdminQuery · does not call while there is no session", async () => {
  const call = vi.fn(async (auth: AdminAuth) => auth);
  const { result } = renderHook(() => useAdminQuery(keyFor, call), {
    wrapper: wrapperWith(false),
  });

  await new Promise((resolve) => setTimeout(resolve, 10));
  expect(call).not.toHaveBeenCalled();
  expect(result.current.isPending).toBe(true);
});

it("useAdminQuery · does not call when the call is undefined", async () => {
  const { result } = renderHook(() => useAdminQuery(keyFor, undefined), {
    wrapper: wrapperWith(true),
  });

  await new Promise((resolve) => setTimeout(resolve, 10));
  expect(result.current.isPending).toBe(true);
});

it("useAdminQuery · honours enabled: false from options", async () => {
  const call = vi.fn(async (auth: AdminAuth) => auth);
  renderHook(() => useAdminQuery(keyFor, call, { enabled: false }), {
    wrapper: wrapperWith(true),
  });

  await new Promise((resolve) => setTimeout(resolve, 10));
  expect(call).not.toHaveBeenCalled();
});
