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

it("NotFoundView · explains the miss and links back to the documents", async () => {
  window.localStorage.setItem("locale", "en");
  renderWithProviders(<NotFoundView />);

  expect(
    await screen.findByText("This address is not part of Redtape."),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "Browse Documents" }),
  ).toHaveAttribute("href", "/documents");
});

it("NotFoundView · speaks German under the de locale", async () => {
  window.localStorage.setItem("locale", "de");
  renderWithProviders(<NotFoundView />);

  expect(
    await screen.findByRole("heading", { name: "Seite nicht gefunden" }),
  ).toBeInTheDocument();
});
