import { expect, it } from "vitest";

import { candidateDetailFixture } from "../../../test/candidateFixtures";
import { candidateCaptures, candidateScreenshotUrl } from "./candidatesApi";

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

it("captures are the screenshot history, newest first, at absolute capture URLs", () => {
  const captures = candidateCaptures(
    candidateDetailFixture({
      screenshots: [
        {
          url: "/api/v1/candidates/c1/screenshots/new",
          fetched_at: "2026-10-02T10:00:00Z",
        },
        {
          url: "/api/v1/candidates/c1/screenshots/old",
          fetched_at: "2026-09-01T10:00:00Z",
        },
      ],
    }),
  );

  expect(captures.map((capture) => capture.fetchedAt)).toEqual([
    "2026-10-02T10:00:00Z",
    "2026-09-01T10:00:00Z",
  ]);
  expect(new URL(captures[1].src).pathname).toBe(
    "/api/v1/candidates/c1/screenshots/old",
  );
});

it("an API that predates the history falls back to the newest screenshot", () => {
  const captures = candidateCaptures(
    candidateDetailFixture({
      screenshots: undefined,
      screenshot: { url: "/shot", fetched_at: "2026-10-01T10:00:00Z" },
    }),
  );

  expect(captures).toEqual([
    {
      src: candidateScreenshotUrl("c1"),
      fetchedAt: "2026-10-01T10:00:00Z",
    },
  ]);
});

it("a candidate without any screenshot has no captures", () => {
  const captures = candidateCaptures(
    candidateDetailFixture({ screenshot: null, screenshots: [] }),
  );

  expect(captures).toEqual([]);
});
