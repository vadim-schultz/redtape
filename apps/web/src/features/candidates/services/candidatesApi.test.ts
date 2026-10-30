import { expect, it } from "vitest";

import { candidateScreenshotUrl } from "./candidatesApi";

it("candidate screenshot url points at the proxy route", () => {
  expect(candidateScreenshotUrl("c1")).toMatch(
    /^https?:\/\/[^/]+\/api\/v1\/candidates\/c1\/screenshot$/,
  );
});

it("candidate screenshot url escapes an id that is not path safe", () => {
  const url = new URL(candidateScreenshotUrl("a/b?x"));

  expect(url.pathname).toBe("/api/v1/candidates/a%2Fb%3Fx/screenshot");
  expect(url.search).toBe("");
});
