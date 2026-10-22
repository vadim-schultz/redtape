import { screen } from "@testing-library/react";
import { it, expect } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";
import ForbiddenView from "./ForbiddenView";

it("ForbiddenView · explains the denial and links back to the documents", async () => {
  window.localStorage.setItem("locale", "en");
  renderWithProviders(<ForbiddenView />);

  expect(
    await screen.findByRole("heading", { name: "Access denied" }),
  ).toBeInTheDocument();
  expect(
    screen.getByText("You don't have permission to view this page."),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "Browse Documents" }),
  ).toHaveAttribute("href", "/documents");
});
