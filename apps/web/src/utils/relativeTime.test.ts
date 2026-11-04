import { expect, it } from "vitest";

import { formatRelativeTime, formatTimeUntil } from "./relativeTime";

const NOW = new Date("2026-09-28T12:00:00Z");

it("formatRelativeTime · minutes ago", () => {
  const then = new Date("2026-09-28T11:55:00Z").toISOString();

  expect(formatRelativeTime(then, "en", NOW)).toBe("5 minutes ago");
});

it("formatRelativeTime · hours ago", () => {
  const then = new Date("2026-09-28T09:00:00Z").toISOString();

  expect(formatRelativeTime(then, "en", NOW)).toBe("3 hours ago");
});

it("formatRelativeTime · days ago", () => {
  const then = new Date("2026-09-25T12:00:00Z").toISOString();

  expect(formatRelativeTime(then, "en", NOW)).toBe("3 days ago");
});

it("formatRelativeTime · localizes to German", () => {
  const then = new Date("2026-09-28T11:55:00Z").toISOString();

  expect(formatRelativeTime(then, "de", NOW)).toBe("vor 5 Minuten");
});

const RETRY_NOW = new Date("2026-10-26T12:00:00Z");

it("formatTimeUntil · picks the coarsest whole unit ahead of now", () => {
  expect(formatTimeUntil("2026-10-26T15:30:00Z", "en", RETRY_NOW)).toBe(
    "in 3 hours",
  );
  expect(formatTimeUntil("2026-10-28T13:00:00Z", "en", RETRY_NOW)).toBe(
    "in 2 days",
  );
  expect(formatTimeUntil("2026-10-26T12:00:20Z", "en", RETRY_NOW)).toBe(
    "in 1 minute",
  );
});

it("formatTimeUntil · returns null when unset, due or past", () => {
  expect(formatTimeUntil(null, "en", RETRY_NOW)).toBeNull();
  expect(formatTimeUntil("2026-10-26T12:00:00Z", "en", RETRY_NOW)).toBeNull();
  expect(formatTimeUntil("2026-10-25T12:00:00Z", "en", RETRY_NOW)).toBeNull();
});

it("formatTimeUntil · an unparseable date returns null instead of a false minimum", () => {
  expect(formatTimeUntil("garbage", "en", RETRY_NOW)).toBeNull();
});
