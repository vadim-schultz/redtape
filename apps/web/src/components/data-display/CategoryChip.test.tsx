import { screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";
import CategoryChip from "./CategoryChip";

const category = {
  code: "home-and-housing",
  name: "Home & housing",
  confidence: 0.8,
};

it("CategoryChip · uses the front-page red semantic token", () => {
  renderWithProviders(
    <CategoryChip
      category={category}
      to="/documents?category=home-and-housing"
    />,
  );

  const link = screen.getByRole("link", { name: "Home & housing" });
  const badge = link.closest(".chakra-badge");

  expect(
    getComputedStyle(badge!).getPropertyValue(
      "--chakra-colors-color-palette-fg",
    ),
  ).toContain("primary");
});

it("CategoryChip · links to the category-filtered list", () => {
  renderWithProviders(
    <CategoryChip
      category={category}
      to="/documents?category=home-and-housing"
    />,
  );

  expect(screen.getByRole("link", { name: "Home & housing" })).toHaveAttribute(
    "href",
    "/documents?category=home-and-housing",
  );
});

it("CategoryChip · is not nested inside another interactive element", () => {
  renderWithProviders(
    <CategoryChip
      category={category}
      to="/documents?category=home-and-housing"
    />,
  );

  const link = screen.getByRole("link", { name: "Home & housing" });

  expect(screen.getAllByRole("link")).toHaveLength(1);
  expect(link.querySelector("a")).toBeNull();
});

it.each([0.1, 0.9])(
  "CategoryChip · renders no opacity style at confidence %s",
  (confidence) => {
    renderWithProviders(
      <CategoryChip
        category={{ ...category, confidence }}
        to="/documents?category=home-and-housing"
      />,
    );

    const badge = screen
      .getByRole("link", { name: "Home & housing" })
      .closest<HTMLElement>(".chakra-badge");

    expect(badge!.style.opacity).toBe("");
  },
);
