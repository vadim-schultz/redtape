import { expect, it } from "vitest";

import { formatDate, formatDateTime } from "./formatDate";

it("formatDate · renders the calendar date in the locale", () => {
  expect(formatDate("2026-10-26T12:00:00Z", "en")).toMatch(/Oct 26, 2026/);
  expect(formatDate("2026-10-26T12:00:00Z", "de")).toMatch(/26\.10\.2026/);
});

it("formatDate · returns an empty string for an unparseable date", () => {
  expect(formatDate("not a date", "en")).toBe("");
});

it("formatDate · renders the Russian month name", () => {
  expect(formatDate("2026-10-26T12:00:00Z", "ru")).toMatch(/26 окт\. 2026/);
});

it("formatDate · an unknown locale uses the default locale's format", () => {
  expect(formatDate("2026-10-26T12:00:00Z", "fr")).toMatch(/26\.10\.2026/);
});

it("formatDateTime · renders date and time in the locale", () => {
  expect(formatDateTime("2026-10-26T12:30:00Z", "de", "UTC")).toBe(
    "26.10.2026, 12:30:00",
  );
});

it("formatDateTime · returns an empty string for an unparseable date", () => {
  expect(formatDateTime("nope", "de")).toBe("");
});
