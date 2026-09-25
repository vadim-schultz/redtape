import { expect, it } from "vitest";

import { buildCellIndex, cellKey } from "./buildCellIndex";

it("buildCellIndex · looks up a count by domain and situation", () => {
  const index = buildCellIndex([{ domain: "d1", situation: "s1", count: 3 }]);

  expect(index.get(cellKey("d1", "s1"))).toBe(3);
});

it("buildCellIndex · unrelated pairs stay undefined", () => {
  const index = buildCellIndex([{ domain: "d1", situation: "s1", count: 3 }]);

  expect(index.get(cellKey("d1", "s2"))).toBeUndefined();
  expect(index.get(cellKey("d2", "s1"))).toBeUndefined();
});
