import { screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";
import BrandButton from "./BrandButton";

it("BrandButton · links to /", async () => {
  renderWithProviders(<BrandButton />);

  expect(await screen.findByRole("link", { name: "Home" })).toHaveAttribute(
    "href",
    "/",
  );
});

it("BrandButton · has accessible name nav.home, svg is aria-hidden", async () => {
  const { container } = renderWithProviders(<BrandButton />);

  await screen.findByRole("link", { name: "Home" });
  expect(container.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
});

it("BrandButton · name follows the active locale", async () => {
  window.localStorage.setItem("locale", "de");
  renderWithProviders(<BrandButton />);

  expect(
    await screen.findByRole("link", { name: "Startseite" }),
  ).toBeInTheDocument();
});

it("BrandButton · mark colour is the brand.mark token", async () => {
  renderWithProviders(<BrandButton />);

  const link = await screen.findByRole("link", { name: "Home" });

  expect(getComputedStyle(link).color).toBe("var(--chakra-colors-brand-mark)");
});

it("BrandButton · mark fills most of the circle", async () => {
  const { container } = renderWithProviders(<BrandButton />);

  await screen.findByRole("link", { name: "Home" });
  const height = container.querySelector("svg")!.getAttribute("height")!;

  expect(parseInt(height)).toBeGreaterThanOrEqual(62);
});
