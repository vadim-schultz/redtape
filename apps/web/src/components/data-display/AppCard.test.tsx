import { screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";
import AppCard from "./AppCard";

it("AppCard · renders its content inside a card with elevation", () => {
  renderWithProviders(<AppCard>Hello</AppCard>);

  const card = screen.getByText("Hello").closest(".chakra-card__root")!;

  expect(getComputedStyle(card).boxShadow).toBe("var(--chakra-shadows-card)");
});

it("AppCard · with a destination the whole card is a link", () => {
  renderWithProviders(<AppCard to="/documents/x">Hello</AppCard>);

  const link = screen.getByRole("link");

  expect(link).toHaveAttribute("href", "/documents/x");
  expect(link.className).toContain("chakra-card__root");
});

it("AppCard · a linked card animates on hover with theme tokens", () => {
  renderWithProviders(<AppCard to="/x">Hello</AppCard>);

  const style = getComputedStyle(screen.getByRole("link"));

  expect(style.transitionDuration).toBe("var(--chakra-durations-normal)");
  expect(style.transitionTimingFunction).toBe("var(--chakra-easings-ease-out)");
});

it("AppCard · a static card is not a link and has no hover motion", () => {
  renderWithProviders(<AppCard>Hello</AppCard>);

  const card = screen.getByText("Hello").closest(".chakra-card__root")!;

  expect(screen.queryByRole("link")).not.toBeInTheDocument();
  expect(getComputedStyle(card).transitionDuration).not.toBe(
    "var(--chakra-durations-normal)",
  );
});
