import { screen, within } from "@testing-library/react";
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

  const main = within(screen.getByRole("main"));
  expect(main.getByRole("status", { name: "Loading..." })).toHaveAttribute(
    "aria-busy",
    "true",
  );
  expect(
    await screen.findByRole("heading", { name: "Documents" }),
  ).toBeInTheDocument();
});

it("app · renders the floating brand link and menu in the layout", async () => {
  renderAppAt("/documents");

  expect(await screen.findByRole("link", { name: "Home" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Menu" })).toBeInTheDocument();
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

it("app · /matrix shows not-found", async () => {
  renderAppAt("/matrix");

  expect(
    await screen.findByRole("heading", { name: "Page not found" }),
  ).toBeInTheDocument();
});

it("app · /documents still resolves", async () => {
  renderAppAt("/documents");

  expect(
    await screen.findByRole("heading", { name: "Documents" }),
  ).toBeInTheDocument();
});
