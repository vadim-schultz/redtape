import { expect, it } from "vitest";

import { formatNumber } from "./formatNumber";

/** Collapse any space-like separator (NBSP, narrow NBSP) to a plain space. */
function plain(text: string): string {
  return text.replace(/[\u00a0\u202f]/g, " ");
}

it("formatNumber · groups and separates per locale", () => {
  expect(plain(formatNumber(1234.5, "ru"))).toBe("1 234,5");
  expect(formatNumber(1234.5, "de")).toBe("1.234,5");
  expect(formatNumber(1234.5, "en")).toBe("1,234.5");
});

it("formatNumber · keeps at most one decimal", () => {
  expect(formatNumber(1.26, "en")).toBe("1.3");
});

it("formatNumber · an unknown locale uses the default locale's format and does not throw", () => {
  expect(formatNumber(1234.5, "fr")).toBe("1.234,5");
  expect(formatNumber(1234.5, "not a tag!")).toBe("1.234,5");
});
