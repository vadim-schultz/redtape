import { expect, it } from "vitest";

import { ApiRequestError } from "../../../services/api";
import { discoveryAdminGuardOutcome } from "./discoveryAdminGuardOutcome";

const READY = { isPending: false, isError: false, error: null };

function apiError(status: number) {
  return new ApiRequestError({ status, url: "/x", bodyText: "" });
}

it("discoveryAdminGuardOutcome · loading waits", () => {
  expect(discoveryAdminGuardOutcome("loading", READY)).toBe("wait");
});

it("discoveryAdminGuardOutcome · anonymous logs in", () => {
  expect(discoveryAdminGuardOutcome("anonymous", READY)).toBe("login");
});

it("discoveryAdminGuardOutcome · unconfigured auth is reported", () => {
  expect(discoveryAdminGuardOutcome("unconfigured", READY)).toBe(
    "auth-unconfigured",
  );
});

it("discoveryAdminGuardOutcome · authenticated with a pending probe waits", () => {
  expect(
    discoveryAdminGuardOutcome("authenticated", {
      ...READY,
      isPending: true,
    }),
  ).toBe("wait");
});

it("discoveryAdminGuardOutcome · authenticated with a resolved probe allows", () => {
  expect(discoveryAdminGuardOutcome("authenticated", READY)).toBe("allow");
});

it("discoveryAdminGuardOutcome · a 403 probe error is forbidden", () => {
  expect(
    discoveryAdminGuardOutcome("authenticated", {
      isPending: false,
      isError: true,
      error: apiError(403),
    }),
  ).toBe("forbidden");
});

it("discoveryAdminGuardOutcome · a 401 probe error logs in", () => {
  expect(
    discoveryAdminGuardOutcome("authenticated", {
      isPending: false,
      isError: true,
      error: apiError(401),
    }),
  ).toBe("login");
});

it("discoveryAdminGuardOutcome · a 503 probe error is disabled", () => {
  expect(
    discoveryAdminGuardOutcome("authenticated", {
      isPending: false,
      isError: true,
      error: apiError(503),
    }),
  ).toBe("disabled");
});

it("discoveryAdminGuardOutcome · any other probe error is an error", () => {
  expect(
    discoveryAdminGuardOutcome("authenticated", {
      isPending: false,
      isError: true,
      error: apiError(500),
    }),
  ).toBe("error");
});
