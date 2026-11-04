import { screen } from "@testing-library/react";
import { it, expect } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import type { CategoryTag } from "../../../taxonomy/types";
import DocumentTags from "./DocumentTags";

const category = (code: string, name: string, confidence = 1): CategoryTag => ({
  code,
  name,
  confidence,
});

const categories = [
  category("identity-and-documents", "Identity"),
  category("health-and-care", "Health"),
  category("moving-house", "Moving"),
];

it("DocumentTags · renders canonical compact category chips", () => {
  renderWithProviders(<DocumentTags categories={categories} />);

  expect(screen.getAllByRole("link")).toHaveLength(3);
  ["Identity", "Health", "Moving"].forEach((name) =>
    expect(screen.getByText(name)).toBeInTheDocument(),
  );
});

it("DocumentTags · each category chip links to the filtered list", () => {
  renderWithProviders(<DocumentTags categories={categories} />);

  expect(screen.getByRole("link", { name: "Identity" })).toHaveAttribute(
    "href",
    "/documents?category=identity-and-documents",
  );
  expect(screen.getByRole("link", { name: "Moving" })).toHaveAttribute(
    "href",
    "/documents?category=moving-house",
  );
});

it("DocumentTags · renders nothing when categories are empty", () => {
  const { container } = renderWithProviders(<DocumentTags categories={[]} />);

  expect(container.querySelector("a, ul")).not.toBeInTheDocument();
});

it("DocumentTags · threads each tag's confidence through to its badge's opacity", () => {
  renderWithProviders(
    <DocumentTags categories={[category("identity-and-documents", "Identity", 0.4)]} />,
  );

  expect(screen.getByText("Identity").closest("a")!.style.opacity).toBe("0.7");
});
