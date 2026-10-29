import { screen, within } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { longUrl, session, stubAdminApi } from "../../test/adminRoutesApi";
import { emotionRules } from "../../test/emotionRules";
import { expandControlsBesideCount } from "../../test/queryStatusCountRow";
import { renderWithProviders } from "../../test/renderWithProviders";
import { createFakeAuthGateway } from "../auth/services/fakeAuthGateway";
import DiscoveryAdminRoutes from "./routes";

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

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

const populatedRoutes = [
  { route: "documents", table: "Documents", cell: "Personalausweis" },
  { route: "tasks", table: "Crawler tasks", cell: longUrl },
  { route: "catalogue", table: "Catalogue services", cell: "service-1" },
  { route: "coverage", table: "Task queue", cell: "Pending tasks" },
  {
    route: "documents/cand-1",
    table: "Mentions",
    cell: /Bitte Geburtsurkunde/,
  },
];

it.each(populatedRoutes)(
  "admin tables retain the shared shell across routes · $route",
  async ({ route, table, cell }) => {
    stubAdminApi("populated");
    renderRoute(route);

    const element = await screen.findByRole("table", { name: table });
    await within(element).findByText(cell);
    expect(element.closest("[data-section-card]")).not.toBeNull();
    expect(element.parentElement).not.toBeNull();
    expect(element).toHaveAttribute("aria-busy", "false");
    expect(within(element).getAllByRole("columnheader").length).toBeGreaterThan(
      1,
    );
  },
);

const listRoutes = [
  { route: "documents", table: "Documents", empty: "No documents found" },
  { route: "tasks", table: "Crawler tasks", empty: "No tasks in queue" },
  {
    route: "catalogue",
    table: "Catalogue services",
    empty: "No catalogue services",
  },
];

it.each(listRoutes)(
  "admin tables retain the shared shell across routes · empty state of $route",
  async ({ route, table, empty }) => {
    stubAdminApi("empty");
    renderRoute(route);

    const element = await screen.findByRole("table", { name: table });
    const shell = element.closest("[data-section-card]");
    expect(shell).not.toBeNull();
    expect(await within(shell as HTMLElement).findByText(empty)).toBeVisible();
    expect(within(element).getAllByRole("columnheader").length).toBeGreaterThan(
      1,
    );
  },
);

it.each(listRoutes)(
  "admin tables retain the shared shell across routes · error state of $route",
  async ({ route, table }) => {
    stubAdminApi("error");
    renderRoute(route);

    const element = await screen.findByRole("table", { name: table });
    const shell = element.closest("[data-section-card]");
    expect(shell).not.toBeNull();
    expect(
      await within(shell as HTMLElement).findByRole("button", {
        name: "Try again",
      }),
    ).toBeVisible();
    expect(within(element).queryAllByRole("link")).toHaveLength(0);
  },
);

it("populated document count row has no expand control", async () => {
  stubAdminApi("populated");
  renderRoute("documents");

  const count = await screen.findByText("1 document");
  expect(expandControlsBesideCount(count)).toHaveLength(0);
  expect(count.closest("[data-section-card]")).not.toBeNull();
  expect(screen.getByRole("link", { name: "Personalausweis" })).toBeVisible();
});

it("legitimate filter select indicators remain available", async () => {
  stubAdminApi("populated");
  renderRoute("documents");

  await screen.findByText("1 document");
  for (const name of ["Minimum mentions", "Role", "Source"]) {
    const select = screen.getByRole("combobox", { name });
    expect(
      select.parentElement?.querySelector(".chakra-native-select__indicator"),
    ).not.toBeNull();
  }
});

it("legitimate filter select indicators remain available · column filter triggers keep their popover semantics", async () => {
  stubAdminApi("populated");
  renderRoute("tasks");

  await screen.findByRole("table", { name: "Crawler tasks" });
  const trigger = screen.getByRole("button", { name: "Task status" });
  expect(trigger).toHaveAttribute("aria-haspopup", "dialog");
  expect(trigger).toHaveAttribute("aria-expanded", "false");
});

it("narrow admin tables remain horizontally inspectable", async () => {
  stubAdminApi("populated");
  const { user } = renderRoute("tasks");

  const table = await screen.findByRole("table", { name: "Crawler tasks" });
  const scroller = table.parentElement as HTMLElement;
  expect(emotionRules(scroller)).toContain("overflow: auto");
  expect(emotionRules(scroller)).toContain("max-width: 100%");
  expect(within(table).getByText(longUrl)).toBeVisible();

  const sort = within(table).getAllByRole("button")[0];
  for (let tabs = 0; tabs < 30 && document.activeElement !== sort; tabs += 1) {
    await user.tab();
  }
  expect(sort).toHaveFocus();
  expect(scroller).toContainElement(sort);
});
