import { expect, it } from "vitest";

import type { CategoryNode } from "../../taxonomy/types";
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
  expect(params.has("domain")).toBe(false);
  expect(params.has("situation")).toBe(false);
  expect(params.has("group")).toBe(false);
});

it("category filter · unknown URL category does not produce a valid taxonomy selection", () => {
  const params = new URLSearchParams("category=not-a-category");

  expect(readValidCategoryCodes(params, tree)).toEqual([]);
});
