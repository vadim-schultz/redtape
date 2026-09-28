import { expect, it } from "vitest";

import { formatRelativeTime } from "./formatRelativeTime";

const now = new Date("2026-09-28T12:00:00Z");

it("formatRelativeTime · minutes ago", () => {
  const then = new Date("2026-09-28T11:55:00Z").toISOString();

  expect(formatRelativeTime(then, "en", now)).toBe("5 minutes ago");
});

it("formatRelativeTime · hours ago", () => {
  const then = new Date("2026-09-28T09:00:00Z").toISOString();

  expect(formatRelativeTime(then, "en", now)).toBe("3 hours ago");
});

it("formatRelativeTime · days ago", () => {
  const then = new Date("2026-09-25T12:00:00Z").toISOString();

  expect(formatRelativeTime(then, "en", now)).toBe("3 days ago");
});

it("formatRelativeTime · localizes to German", () => {
  const then = new Date("2026-09-28T11:55:00Z").toISOString();

  expect(formatRelativeTime(then, "de", now)).toBe("vor 5 Minuten");
});
