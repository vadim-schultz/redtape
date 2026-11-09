import { expect, it } from "vitest";

import { flattenCategories } from "../../../utils/categoryTree";
import type { CategoryNode } from "../../taxonomy/types";
import { categoryNamesByCode } from "../../taxonomy/utils/categoryNames";
import { readValidCategoryCodes, withToggledCategory } from "./filterParams";

const tree: CategoryNode[] = [
  {
    code: "home-and-housing",
    name: "Home & housing",
    description: "",
    icon: "home",
    parent_code: null,
    children: [
      {
        code: "moving-house",
        name: "Moving house",
        description: "",
        icon: null,
        parent_code: "home-and-housing",
        children: [],
      },
    ],
  },
];

it("category filter · selecting a root serializes one category code", () => {
  const params = withToggledCategory(new URLSearchParams(), "home-and-housing");

  expect(params.toString()).toBe("category=home-and-housing");
});

it("category filter · selecting a subcategory serializes its exact code", () => {
  const params = withToggledCategory(
    new URLSearchParams("category=home-and-housing"),
    "moving-house",
    "home-and-housing",
  );

  expect(params.getAll("category")).toEqual(["moving-house"]);
});

it("category filter · unknown URL category does not produce a valid taxonomy selection", () => {
  const params = new URLSearchParams("category=not-a-category");

  expect(readValidCategoryCodes(params, tree)).toEqual([]);
});

it("category traversal · the URL filter and the name lookup read one traversal of the same tree", () => {
  const everyCode = ["home-and-housing", "moving-house"];
  const params = new URLSearchParams(
    everyCode.map((code) => ["category", code]),
  );

  expect(flattenCategories(tree).map((node) => node.code)).toEqual(everyCode);
  expect(readValidCategoryCodes(params, tree)).toEqual(everyCode);
  expect(Object.keys(categoryNamesByCode(tree))).toEqual(everyCode);
});

it("category filter · an unknown code in the URL leaves the filter as if it were absent", () => {
  const withUnknown = new URLSearchParams(
    "category=moving-house&category=not-a-category",
  );
  const withoutUnknown = new URLSearchParams("category=moving-house");

  expect(readValidCategoryCodes(withUnknown, tree)).toEqual(
    readValidCategoryCodes(withoutUnknown, tree),
  );
  expect(readValidCategoryCodes(withUnknown, tree)).toEqual(["moving-house"]);
});
