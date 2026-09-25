import { screen, within } from "@testing-library/react";
import { it, expect } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";
import AppLayout from "./AppLayout";

it("AppLayout · renders Redtape with appTitle in the header", async () => {
  renderWithProviders(<AppLayout>content</AppLayout>);

  const header = await screen.findByRole("banner");
  const wordmark = within(header).getByRole("link", { name: "Redtape" });

  expect(getComputedStyle(wordmark).fontSize).toBe(
    "var(--chakra-font-sizes-4xl)",
  );
  expect(getComputedStyle(wordmark).color).toBe(
    "var(--chakra-colors-text-heading)",
  );
});

it("AppLayout · wordmark links to home", async () => {
  renderWithProviders(<AppLayout>content</AppLayout>);

  const wordmark = await screen.findByRole("link", { name: "Redtape" });

  expect(wordmark).toHaveAttribute("href", "/");
});

it("AppLayout · renders main landmark with children", async () => {
  renderWithProviders(
    <AppLayout>
      <p>Hello from a page</p>
    </AppLayout>,
  );

  expect(await screen.findByRole("main")).toHaveTextContent(
    "Hello from a page",
  );
});

it("AppLayout · renders header when children empty", async () => {
  renderWithProviders(
    <AppLayout>
      <></>
    </AppLayout>,
  );

  expect(await screen.findByRole("banner")).toBeInTheDocument();
  expect(screen.getByRole("main")).toBeInTheDocument();
});

it("AppLayout · includes color mode toggle control", async () => {
  renderWithProviders(<AppLayout>content</AppLayout>);

  expect(
    await screen.findByRole("button", { name: "Toggle color mode" }),
  ).toBeInTheDocument();
});

it("AppLayout · color mode toggle is labelled in the active locale", async () => {
  window.localStorage.setItem("locale", "de");
  renderWithProviders(<AppLayout>content</AppLayout>);

  expect(
    await screen.findByRole("button", { name: "Farbmodus wechseln" }),
  ).toBeInTheDocument();
});
