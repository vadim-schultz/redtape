import { describe, expect, it } from "vitest";

import {
  BAND_PALETTE,
  HIGH_MIN,
  LOW_MAX,
  bandFor,
  percentOf,
} from "./confidenceBand";

describe("bandFor", () => {
  it.each([
    [0, "low"],
    [0.399, "low"],
    [0.4, "mid"],
    [0.699, "mid"],
    [0.7, "high"],
    [1, "high"],
  ] as const)("%s is %s", (confidence, band) => {
    expect(bandFor(confidence)).toBe(band);
  });

  it("exposes the two thresholds", () => {
    expect([LOW_MAX, HIGH_MIN]).toEqual([0.4, 0.7]);
  });

  it.each([
    [Number.NaN, "low"],
    [Number.POSITIVE_INFINITY, "low"],
    [Number.NEGATIVE_INFINITY, "low"],
    [-0.2, "low"],
    [1.7, "high"],
  ] as const)("clamps %s to the %s band", (confidence, band) => {
    expect(bandFor(confidence)).toBe(band);
  });
});

describe("BAND_PALETTE", () => {
  it("maps bands to the traffic-light palettes", () => {
    expect(BAND_PALETTE).toEqual({ low: "red", mid: "yellow", high: "green" });
  });
});

describe("percentOf", () => {
  it("rounds to a whole percent", () => {
    expect(percentOf(0.456)).toBe(46);
  });

  it.each([
    [Number.NaN, 0],
    [Number.POSITIVE_INFINITY, 0],
    [-0.2, 0],
    [1.7, 100],
  ])("clamps %s to %s", (confidence, percent) => {
    expect(percentOf(confidence)).toBe(percent);
  });
});
