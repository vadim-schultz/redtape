import { expect, it } from "vitest";

import { formatDate } from "./formatDate";

it("formatDate · renders the calendar date in the locale", () => {
  expect(formatDate("2026-10-26T12:00:00Z", "en")).toMatch(/Oct 26, 2026/);
  expect(formatDate("2026-10-26T12:00:00Z", "de")).toMatch(/26\.10\.2026/);
});

it("formatDate · returns an empty string for an unparseable date", () => {
  expect(formatDate("not a date", "en")).toBe("");
});
