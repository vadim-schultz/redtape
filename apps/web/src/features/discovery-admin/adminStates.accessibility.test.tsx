import { focusManager } from "@tanstack/react-query";
import { screen, waitFor, within } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import {
  session,
  stubAdminApi,
  type AdminApiMode,
} from "../../test/adminRoutesApi";
import { renderWithProviders } from "../../test/renderWithProviders";
import { expectAccessibleTables } from "../../test/tableAccessibility";
import { createFakeAuthGateway } from "../auth/services/fakeAuthGateway";
import DiscoveryAdminRoutes from "./routes";

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

const lists = [
  { route: "documents", table: "Documents", row: "Personalausweis" },
  { route: "tasks", table: "Crawler tasks", row: /example\.gov/ },
  { route: "catalogue", table: "Catalogue services", row: "service-1" },
];

function renderRoute(path: string) {
  return renderWithProviders(
    <Routes>
      <Route path="/admin/discovery/*" element={<DiscoveryAdminRoutes />} />
    </Routes>,
    {
      initialEntries: [`/admin/discovery/${path}`],
      authGateway: createFakeAuthGateway({ session }),
    },
  );
}

function shellOf(table: HTMLElement): HTMLElement {
  const shell = table.closest<HTMLElement>("[data-section-card]");
  expect(shell).not.toBeNull();
  return shell as HTMLElement;
}

/** The text a user can read in the table body, without the header row. */
function bodyText(table: HTMLElement): string {
  const [, ...rows] = within(table).getAllByRole("row");
  return rows
    .map((row) => row.textContent ?? "")
    .join("")
    .trim();
}

async function openTable(mode: AdminApiMode, route: string, name: string) {
  stubAdminApi(mode);
  const rendered = renderRoute(route);
  const table = await screen.findByRole("table", { name });
  return { ...rendered, table };
}

it.each(lists)(
  "full admin state matrix has no silent blank result · loading $route",
  async ({ route, table: name }) => {
    const { table } = await openTable("loading", route, name);

    expect(table).toHaveAttribute("aria-busy", "true");
    expect(
      within(shellOf(table)).getByRole("status", { name: "Loading..." }),
    ).toBeVisible();
    expectAccessibleTables(shellOf(table));
  },
);

it.each(lists)(
  "full admin state matrix has no silent blank result · populated $route",
  async ({ route, table: name, row }) => {
    const { table } = await openTable("populated", route, name);

    await within(table).findByText(row);
    expect(bodyText(table)).not.toBe("");
    expectAccessibleTables(shellOf(table));
  },
);

it.each(lists)(
  "full admin state matrix has no silent blank result · empty $route",
  async ({ route, table: name }) => {
    const { table } = await openTable("empty", route, name);

    await waitFor(() => expect(bodyText(table)).not.toBe(""));
    expect(table).toHaveAttribute("aria-busy", "false");
    expectAccessibleTables(shellOf(table));
  },
);

it.each(lists)(
  "full admin state matrix has no silent blank result · error $route",
  async ({ route, table: name }) => {
    const { table } = await openTable("error", route, name);

    await within(shellOf(table)).findByRole("button", { name: "Try again" });
    expect(bodyText(table)).not.toBe("");
    expectAccessibleTables(shellOf(table));
  },
);

it.each(lists)(
  "full admin state matrix has no silent blank result · refreshing $route",
  async ({ route, table: name, row }) => {
    const { table } = await openTable("refreshing", route, name);
    await within(table).findByText(row);

    focusManager.setFocused(false);
    focusManager.setFocused(true);

    await waitFor(() => expect(table).toHaveAttribute("aria-busy", "true"));
    expect(within(table).getByText(row)).toBeVisible();
    expectAccessibleTables(shellOf(table));
  },
);
