import { expect, it } from "vitest";

import { AUTH_GATE } from "./authGate";

it("authGate · maps every AuthStatus", () => {
  expect(AUTH_GATE).toEqual({
    loading: "wait",
    anonymous: "login",
    unconfigured: "unconfigured",
    authenticated: "open",
  });
});
