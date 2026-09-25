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

it("app · shows a list skeleton while the documents page code loads", async () => {
  window.localStorage.setItem("locale", "en");
  renderAppAt("/documents");

  expect(screen.getByRole("status", { name: "Loading..." })).toHaveAttribute(
    "aria-busy",
    "true",
  );
  expect(
    await screen.findByRole("heading", { name: "Documents" }),
  ).toBeInTheDocument();
});

it("app · renders Redtape in the layout header", async () => {
  renderAppAt("/documents");

  expect(await screen.findByRole("banner")).toHaveTextContent("Redtape");
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
