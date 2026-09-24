import { screen } from "@testing-library/react";
import { it, expect } from "vitest";

import { renderWithProviders } from "../test/renderWithProviders";
import NotFoundView from "./NotFoundView";

it("NotFoundView · heading uses the bold pageTitle style", async () => {
  renderWithProviders(<NotFoundView />);

  const heading = await screen.findByRole("heading", {
    name: "Page not found",
  });

  expect(getComputedStyle(heading).fontWeight).toBe(
    "var(--chakra-font-weights-bold)",
  );
  expect(getComputedStyle(heading).color).toBe(
    "var(--chakra-colors-text-heading)",
  );
});
