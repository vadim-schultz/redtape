import { expect, it } from "vitest";

import { ApiRequestError } from "./api";
import { isNotFound, isUnprocessable } from "./apiErrors";

function apiError(status: number) {
  return new ApiRequestError({ status, url: "/x", bodyText: "" });
}

it("isNotFound · true for a 404 ApiRequestError", () => {
  expect(isNotFound(apiError(404))).toBe(true);
});

it("isNotFound · false for 500, network errors, and non-errors", () => {
  expect(isNotFound(apiError(500))).toBe(false);
  expect(isNotFound(new TypeError("Failed to fetch"))).toBe(false);
  expect(isNotFound(null)).toBe(false);
  expect(isNotFound({ status: 404 })).toBe(false);
});

it("isUnprocessable · true only for a 422 ApiRequestError", () => {
  expect(isUnprocessable(apiError(422))).toBe(true);
  expect(isUnprocessable(apiError(404))).toBe(false);
  expect(isUnprocessable(undefined)).toBe(false);
});
