import { describe, expect, it } from "vitest";

import { ariaSortFor, nextSort } from "./sorting";

describe("nextSort", () => {
  it("starts an unsorted column ascending", () => {
    expect(nextSort({}, "name")).toEqual({ sortBy: "name", sortOrder: "asc" });
  });

  it("toggles the active column between ascending and descending", () => {
    const asc = { sortBy: "name", sortOrder: "asc" } as const;
    const desc = nextSort(asc, "name");

    expect(desc).toEqual({ sortBy: "name", sortOrder: "desc" });
    expect(nextSort(desc, "name")).toEqual(asc);
  });

  it("restarts ascending when another column becomes active", () => {
    const current = { sortBy: "name", sortOrder: "desc" } as const;

    expect(nextSort(current, "count")).toEqual({
      sortBy: "count",
      sortOrder: "asc",
    });
  });
});

describe("ariaSortFor", () => {
  const current = { sortBy: "name", sortOrder: "desc" } as const;

  it("reports the active column order", () => {
    expect(ariaSortFor(current, "name")).toBe("descending");
  });

  it("reports none for other sortable columns and nothing for display columns", () => {
    expect(ariaSortFor(current, "count")).toBe("none");
    expect(ariaSortFor(current, undefined)).toBeUndefined();
  });
});
