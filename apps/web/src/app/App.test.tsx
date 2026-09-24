import { screen } from "@testing-library/react";
import { it, expect } from "vitest";

import AppLayout from "../components/layout/AppLayout";
import { renderWithProviders } from "../test/renderWithProviders";
import App from "./App";

function renderAppAt(path: string) {
  return renderWithProviders(
    <AppLayout>
      <App />
    </AppLayout>,
    { initialEntries: [path] },
  );
}

it("app · renders RedTape in the layout header", async () => {
  renderAppAt("/documents");

  expect(await screen.findByRole("banner")).toHaveTextContent("RedTape");
});

it("app · renders not-found for an unregistered path", async () => {
  renderAppAt("/nope");

  expect(
    await screen.findByRole("heading", { name: "Page not found" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("heading", { name: "documents.list_title" }),
  ).not.toBeInTheDocument();
});

it("app · not-found exposes a landmark main region", async () => {
  renderAppAt("/nope");

  expect(await screen.findByRole("main")).toHaveTextContent("Page not found");
});
