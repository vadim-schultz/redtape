import { expect, it } from "vitest";

import { buildAxis } from "./buildAxis";

const term = (code: string) => ({
  code,
  name: code.toUpperCase(),
  description: "",
  icon: null,
});

it("buildAxis · keeps taxonomy order and takes totals from the response", () => {
  const axis = buildAxis(
    [term("a"), term("b"), term("c")],
    [
      { code: "c", count: 1 },
      { code: "a", count: 9 },
    ],
  );

  expect(axis).toEqual([
    { code: "a", name: "A", total: 9 },
    { code: "c", name: "C", total: 1 },
  ]);
});

it("buildAxis · drops terms absent from the response", () => {
  expect(buildAxis([term("a")], [])).toEqual([]);
});
