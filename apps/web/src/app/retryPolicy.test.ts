import { describe, expect, it } from "vitest";

import { ApiRequestError } from "../services/api";
import { retryDelay, shouldRetry } from "./retryPolicy";

const apiError = (status: number) =>
  new ApiRequestError({ status, url: "/x", bodyText: "" });

describe("shouldRetry", () => {
  it("retries network failures and 5xx while the server may be waking up", () => {
    expect(shouldRetry(0, new TypeError("Failed to fetch"))).toBe(true);
    expect(shouldRetry(3, apiError(503))).toBe(true);
  });

  it("never retries client errors such as 404", () => {
    expect(shouldRetry(0, apiError(404))).toBe(false);
    expect(shouldRetry(0, apiError(422))).toBe(false);
  });

  it("gives up after five retries", () => {
    expect(shouldRetry(5, apiError(503))).toBe(false);
  });
});

describe("retryDelay", () => {
  it("backs off exponentially up to eight seconds", () => {
    expect([0, 1, 2, 3, 4, 9].map(retryDelay)).toEqual([
      1000, 2000, 4000, 8000, 8000, 8000,
    ]);
  });
});
