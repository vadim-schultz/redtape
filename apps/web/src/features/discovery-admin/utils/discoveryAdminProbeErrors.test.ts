import { describe, expect, it } from "vitest";

import { ApiRequestError } from "../../../services/api";
import { isDiscoveryAdminUnavailable } from "./discoveryAdminProbeErrors";

function apiError(status: number) {
  return new ApiRequestError({ status, url: "/x", bodyText: "" });
}

describe("isDiscoveryAdminUnavailable", () => {
  it.each([
    ["a 503", apiError(503)],
    ["a 500", apiError(500)],
    ["a network failure", new TypeError("Failed to fetch")],
  ])("treats %s as unavailable", (_label, error) => {
    expect(isDiscoveryAdminUnavailable(error)).toBe(true);
  });

  it.each([
    ["a 401", apiError(401)],
    ["a 403", apiError(403)],
  ])("does not treat %s as unavailable", (_label, error) => {
    expect(isDiscoveryAdminUnavailable(error)).toBe(false);
  });
});
