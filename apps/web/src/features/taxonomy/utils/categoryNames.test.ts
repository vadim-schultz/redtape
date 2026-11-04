import { expect, it } from "vitest";

import type { CategoryNode } from "../types";
import { categoryNamesByCode } from "./categoryNames";

const tree: CategoryNode[] = [
  {
    code: "home-and-housing",
    name: "Wohnen",
    description: "",
    icon: null,
    parent_code: null,
    children: [
      {
        code: "moving-house",
        name: "Umzug",
        description: "",
        icon: null,
        parent_code: "home-and-housing",
        children: [],
      },
    ],
  },
];

it("categoryNamesByCode · maps roots and subcategories to their localized names", () => {
  expect(categoryNamesByCode(tree)).toEqual({
    "home-and-housing": "Wohnen",
    "moving-house": "Umzug",
  });
});

it("categoryNamesByCode · no tree yields no names, so codes are shown instead", () => {
  expect(categoryNamesByCode(undefined)).toEqual({});
  expect(categoryNamesByCode([])).toEqual({});
});

it("categoryNamesByCode · a malformed response yields no names instead of throwing", () => {
  const malformed = { detail: "not a tree" } as unknown as CategoryNode[];

  expect(categoryNamesByCode(malformed)).toEqual({});
});
