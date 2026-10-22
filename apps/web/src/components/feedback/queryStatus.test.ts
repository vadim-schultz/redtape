import { expect, it, vi } from "vitest";

import { toQueryStatus } from "./queryStatus";

function queryOf(overrides: Partial<Parameters<typeof toQueryStatus>[0]> = {}) {
  return {
    isLoading: false,
    isFetching: false,
    isError: false,
    error: null,
    refetch: vi.fn(() => Promise.resolve()),
    ...overrides,
  };
}

it("toQueryStatus · a loading query is loading, not refreshing", () => {
  const status = toQueryStatus(queryOf({ isLoading: true, isFetching: true }));

  expect(status.isLoading).toBe(true);
  expect(status.isRefreshing).toBe(false);
  expect(status.isError).toBe(false);
});

it("toQueryStatus · a background refetch is refreshing, not loading", () => {
  const status = toQueryStatus(queryOf({ isFetching: true }));

  expect(status.isRefreshing).toBe(true);
  expect(status.isLoading).toBe(false);
});

it("toQueryStatus · onRetry calls refetch", () => {
  const query = queryOf();

  toQueryStatus(query).onRetry();

  expect(query.refetch).toHaveBeenCalledOnce();
});

it("toQueryStatus · an error query exposes the error and still retries", () => {
  const boom = new Error("boom");
  const query = queryOf({ isError: true, error: boom });

  const status = toQueryStatus(query);
  status.onRetry();

  expect(status.isError).toBe(true);
  expect(status.error).toBe(boom);
  expect(query.refetch).toHaveBeenCalledOnce();
});

it("toQueryStatus · a settled query exposes no error and is idle", () => {
  const status = toQueryStatus(queryOf());

  expect(status).toMatchObject({
    isLoading: false,
    isRefreshing: false,
    isError: false,
    error: null,
  });
});
