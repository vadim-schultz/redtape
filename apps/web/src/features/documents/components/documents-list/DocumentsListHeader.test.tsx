import { screen } from "@testing-library/react";
import { it, expect } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import DocumentsListHeader from "./DocumentsListHeader";

it("DocumentsListHeader · renders title with pageTitle style", async () => {
  renderWithProviders(<DocumentsListHeader title="Documents" />);

  const heading = await screen.findByRole("heading", { name: "Documents" });

  expect(getComputedStyle(heading).fontFamily).toBe(
    "var(--chakra-fonts-heading)",
  );
  expect(getComputedStyle(heading).fontWeight).toBe(
    "var(--chakra-font-weights-bold)",
  );
  expect(getComputedStyle(heading).color).toBe(
    "var(--chakra-colors-text-heading)",
  );
});
