import { describe, expect, it } from "vitest";

import {
  currentPage,
  isNavigablePage,
  offsetForPage,
  pageCount,
  rangeOf,
} from "./pagination";

describe("page math", () => {
  it("derives page count, current page, and offsets", () => {
    expect(pageCount(101, 20)).toBe(6);
    expect(currentPage(40, 20)).toBe(3);
    expect(offsetForPage(3, 20)).toBe(40);
  });

  it("clamps the displayed range to the total", () => {
    expect(rangeOf({ offset: 100, limit: 20, total: 101 })).toEqual({
      from: 101,
      to: 101,
    });
  });
});

describe("page validity", () => {
  const page = { offset: 20, limit: 20, total: 60 };

  it("accepts pages inside the result", () => {
    expect(isNavigablePage(page, 1)).toBe(true);
    expect(isNavigablePage(page, 3)).toBe(true);
  });

  it("rejects pages outside the result and non-integers", () => {
    expect(isNavigablePage(page, 0)).toBe(false);
    expect(isNavigablePage(page, 4)).toBe(false);
    expect(isNavigablePage(page, 1.5)).toBe(false);
  });

  it("treats an empty or non-positive size as zero pages", () => {
    expect(pageCount(0, 20)).toBe(0);
    expect(pageCount(10, 0)).toBe(0);
  });
});
