import { screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../../../test/renderWithProviders";
import type { DocumentFilters } from "../../../hooks/useDocumentFilters";
import type { CategoryNode } from "../../../../taxonomy/types";
import CategoryFilterView from "./CategoryFilterView";

const categories: CategoryNode[] = [
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

function filters(selected: string[] = []): DocumentFilters {
  return {
    categories: selected,
    legacy: { domain: [], group: [], situation: [] },
    toggleCategory: vi.fn(),
    clear: vi.fn(),
    clearAll: vi.fn(),
  };
}

it("category filter · selecting a root reveals its subcategories", async () => {
  const state = filters();
  const { user } = renderWithProviders(
    <CategoryFilterView categories={categories} filters={state} />,
  );

  await user.click(screen.getByRole("button", { name: "Home & housing" }));

  expect(state.toggleCategory).toHaveBeenCalledWith("home-and-housing");
  expect(screen.getByRole("button", { name: "Moving house" })).toBeVisible();
});

it("category filter · selecting a subcategory has no legacy axis alias", async () => {
  const state = filters(["home-and-housing"]);
  const { user } = renderWithProviders(
    <CategoryFilterView categories={categories} filters={state} />,
  );

  await user.click(screen.getByRole("button", { name: "Moving house" }));

  expect(state.toggleCategory).toHaveBeenCalledWith(
    "moving-house",
    "home-and-housing",
  );
  expect(state.legacy).toEqual({ domain: [], group: [], situation: [] });
});

it("category filter · unknown URL category is not shown as selected", () => {
  renderWithProviders(
    <CategoryFilterView categories={categories} filters={filters(["ghost"])} />,
  );

  expect(
    screen.getByRole("button", { name: "Home & housing" }),
  ).toHaveAttribute("aria-pressed", "false");
});
