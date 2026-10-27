import { expect, it } from "vitest";

import { formatBytes } from "./formatBytes";

it("formatBytes · scales to the largest whole unit with locale digits", () => {
  expect(formatBytes(0, "en")).toBe("0 B");
  expect(formatBytes(1536, "en")).toBe("1.5 KB");
  expect(formatBytes(1536, "de")).toBe("1,5 KB");
  expect(formatBytes(8 * 1024 ** 3, "en")).toBe("8 GB");
});

it("formatBytes · clamps negative and non-finite sizes to zero", () => {
  expect(formatBytes(-5, "en")).toBe("0 B");
  expect(formatBytes(Number.NaN, "en")).toBe("0 B");
});
