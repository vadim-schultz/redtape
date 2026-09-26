import { screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";
import AppLayout from "./AppLayout";

it("AppLayout · renders no banner landmark", async () => {
  renderWithProviders(<AppLayout>content</AppLayout>);

  await screen.findByRole("main");
  expect(screen.queryByRole("banner")).not.toBeInTheDocument();
});

it("AppLayout · renders children inside main", async () => {
  renderWithProviders(
    <AppLayout>
      <p>Hello from a page</p>
    </AppLayout>,
  );

  expect(await screen.findByRole("main")).toHaveTextContent(
    "Hello from a page",
  );
});

it("AppLayout · mounts the floating brand link and menu button", async () => {
  renderWithProviders(<AppLayout>content</AppLayout>);

  expect(await screen.findByRole("link", { name: "Home" })).toHaveAttribute(
    "href",
    "/",
  );
  expect(screen.getByRole("button", { name: "Menu" })).toBeInTheDocument();
});

it("AppLayout · has no toolbar links (matrix, browse) left", async () => {
  renderWithProviders(<AppLayout>content</AppLayout>);

  await screen.findByRole("main");
  expect(
    screen.queryByRole("link", { name: "Matrix" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("link", { name: /browse/i }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("link", { name: "Redtape" }),
  ).not.toBeInTheDocument();
});
