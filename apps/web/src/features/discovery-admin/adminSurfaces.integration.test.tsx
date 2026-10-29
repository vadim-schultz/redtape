import { screen, waitFor, within } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { mention } from "../../test/discoveryAdminFixtures";
import { expandControlsBesideCount } from "../../test/queryStatusCountRow";
import { renderWithProviders } from "../../test/renderWithProviders";
import { createFakeAuthGateway } from "../auth/services/fakeAuthGateway";
import { baseCoverage } from "./components/coverage/coverageFixture";
import DiscoveryAdminRoutes from "./routes";

type Mode = "populated" | "empty" | "error";

const session = {
  accessToken: "token-1",
  userId: "user-1",
  email: "admin@example.com",
};
const admin = "/api/v1/discovery/admin";
const longUrl = `https://example.gov/${"very-long-segment/".repeat(12)}end`;

const candidate = {
  id: "cand-1",
  jurisdiction_id: "jur-1",
  key: "personalausweis",
  title_i18n: { en: "Personalausweis" },
  official_url: null,
  status: "staged",
  suggestion_id: null,
  mention_count: 7,
  roles: ["form"],
  jurisdiction_name_i18n: { en: "Germany" },
  created_at: "2026-01-01T12:00:00Z",
  updated_at: "2026-01-01T12:00:00Z",
};
const task = {
  id: "task-1",
  catalogue_service_id: "cat-1",
  source: "govdata",
  kind: "fetch_url",
  target_url: longUrl,
  status: "pending",
  priority: 100,
  attempt_count: 0,
  not_before: null,
  input_key: null,
  lease_expires_at: null,
  created_at: "2026-01-01T12:00:00Z",
  updated_at: "2026-01-01T12:00:00Z",
};
const service = {
  id: "catalogue-1",
  source: "govdata",
  external_id: "service-1",
  jurisdiction_id: "jur-1",
  title_i18n: { en: "Example service" },
  pipeline_stage: "T3",
  portal_url: longUrl,
  created_at: "2026-01-01T12:00:00Z",
  updated_at: "2026-01-01T12:00:00Z",
};
const detail = {
  candidate: { ...candidate, mention_count: 1 },
  jurisdiction_name_i18n: { en: "Germany" },
  mentions: [mention({ excerpt: "Bitte Geburtsurkunde mitbringen" })],
  suggested_domain_codes: [],
  suggested_situation_codes: [],
};

const skippedPreview = {
  candidate_id: "cand-1",
  suggestion: null,
  suggestion_id: null,
  skip_reason: "no_mentions",
  conflicts: [],
};

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function paged(items: unknown[], extra = {}) {
  return { items, total: items.length, offset: 0, limit: 20, ...extra };
}

function bodyFor(path: string, mode: Mode): unknown {
  const rows = (item: unknown) => (mode === "empty" ? [] : [item]);
  if (path.endsWith("/me")) {
    return { id: "user-1", email: session.email, role: "user" };
  }
  if (path.endsWith(`${admin}/tasks`)) return paged(rows(task));
  if (path.endsWith(`${admin}/candidates`)) return paged(rows(candidate));
  if (path.endsWith(`${admin}/candidates/cand-1`)) return detail;
  if (path.endsWith("/emit-preview")) return skippedPreview;
  if (path.endsWith(`${admin}/catalogue`)) {
    const summary = { total: 1, by_source: {}, by_pipeline_stage: {} };
    return paged(rows(service), { summary, limit: 50 });
  }
  if (path.endsWith(`${admin}/coverage`)) return baseCoverage;
  return { items: [], total: 0, offset: 0, limit: 20 };
}

function isListPath(path: string): boolean {
  return [`${admin}/tasks`, `${admin}/candidates`, `${admin}/catalogue`].some(
    (list) => path.endsWith(list),
  );
}

/** Serves every admin endpoint; in `error` mode the list endpoints fail but the admin probe and coverage pass. */
function stubAdminApi(mode: Mode) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input?: unknown) => {
      const url = new URL(String(input));
      const isProbe = url.searchParams.get("limit") === "1";
      const failing = mode === "error" && !isProbe && isListPath(url.pathname);
      if (failing) return new Response("", { status: 500 });
      return new Response(JSON.stringify(bodyFor(url.pathname, mode)));
    }),
  );
}

/** jsdom ignores `@layer` rules in computed style, so read the declarations Emotion injected. */
function declaredStyle(element: HTMLElement): string {
  const selector = `.${element.classList[0]}`;
  return Array.from(document.styleSheets)
    .flatMap((sheet) => Array.from(sheet.cssRules))
    .map((rule) => rule.cssText)
    .filter((css) => css.includes(selector))
    .join(" ");
}

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
  expect(declaredStyle(scroller)).toContain("overflow: auto");
  expect(declaredStyle(scroller)).toContain("max-width: 100%");
  expect(within(table).getByText(longUrl)).toBeVisible();

  const sort = within(table).getAllByRole("button")[0];
  await user.tab();
  while (
    document.activeElement !== sort &&
    document.activeElement !== document.body
  ) {
    await user.tab();
  }
  expect(sort).toHaveFocus();
  await waitFor(() => expect(scroller).toContainElement(sort));
});
