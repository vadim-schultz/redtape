import { screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";
import FloatingControls from "./FloatingControls";

it("FloatingControls · shows the brand link and the menu button", async () => {
  renderWithProviders(<FloatingControls />);

  expect(await screen.findByRole("link", { name: "Home" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Menu" })).toBeInTheDocument();
});

it("FloatingControls · buttons are fixed-position circles", async () => {
  renderWithProviders(<FloatingControls />);

  const link = await screen.findByRole("link", { name: "Home" });
  const burger = screen.getByRole("button", { name: "Menu" });

  for (const el of [link, burger]) {
    expect(el.parentElement).toHaveStyle({ position: "fixed" });
    expect(getComputedStyle(el).borderRadius).toBe("var(--chakra-radii-full)");
  }
});
