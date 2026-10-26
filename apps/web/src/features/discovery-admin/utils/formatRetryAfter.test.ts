import { expect, it } from "vitest";

import { formatRetryAfter } from "./formatRetryAfter";

const NOW = new Date("2026-10-26T12:00:00Z");

it("formatRetryAfter · picks the coarsest whole unit ahead of now", () => {
  expect(formatRetryAfter("2026-10-26T15:30:00Z", "en", NOW)).toBe(
    "in 3 hours",
  );
  expect(formatRetryAfter("2026-10-28T13:00:00Z", "en", NOW)).toBe("in 2 days");
  expect(formatRetryAfter("2026-10-26T12:00:20Z", "en", NOW)).toBe(
    "in 1 minute",
  );
});

it("formatRetryAfter · returns null when unset, due or past", () => {
  expect(formatRetryAfter(null, "en", NOW)).toBeNull();
  expect(formatRetryAfter("2026-10-26T12:00:00Z", "en", NOW)).toBeNull();
  expect(formatRetryAfter("2026-10-25T12:00:00Z", "en", NOW)).toBeNull();
});
