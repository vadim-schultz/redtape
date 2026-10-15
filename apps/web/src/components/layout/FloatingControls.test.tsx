import { screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";
import FloatingControls from "./FloatingControls";

it("FloatingControls · renders only the menu trigger on the right", async () => {
  renderWithProviders(<FloatingControls />);

  expect(screen.queryByRole("link", { name: "Home" })).not.toBeInTheDocument();
  expect(
    await screen.findByRole("button", { name: "Menu" }),
  ).toBeInTheDocument();
});

it("FloatingControls · buttons are fixed-position circles", async () => {
  renderWithProviders(<FloatingControls />);

  const menuTrigger = await screen.findByRole("button", { name: "Menu" });

  expect(menuTrigger.parentElement).toHaveStyle({ position: "fixed" });
  expect(getComputedStyle(menuTrigger).borderRadius).toBe(
    "var(--chakra-radii-full)",
  );
});
