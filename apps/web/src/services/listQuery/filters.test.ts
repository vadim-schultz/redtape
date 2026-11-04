import { describe, expect, it } from "vitest";

import { oneOfFilter } from "./filters";

const parse = oneOfFilter(["pending", "approved"] as const);

describe("oneOfFilter", () => {
  it("accepts a listed value and returns it typed", () => {
    expect(parse("approved")).toBe("approved");
  });

  it("rejects an unlisted value", () => {
    expect(parse("bogus")).toBeUndefined();
  });

  it("rejects the empty string", () => {
    expect(parse("")).toBeUndefined();
  });

  it("is case sensitive", () => {
    expect(parse("Approved")).toBeUndefined();
  });
});
