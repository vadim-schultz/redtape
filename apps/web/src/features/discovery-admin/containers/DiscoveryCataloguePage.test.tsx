import { screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import { createFakeAuthGateway } from "../../auth/services/fakeAuthGateway";
import type { AuthSession } from "../../auth/services/authGateway";
import DiscoveryCataloguePage from "./DiscoveryCataloguePage";

const session: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "admin@example.com",
};

const catalogueResponse = {
  items: [
    {
      id: "catalogue-1",
      source: "govdata",
      external_id: "service-1",
      jurisdiction_id: "jurisdiction-1",
      title_i18n: { en: "Example service" },
      pipeline_stage: "T3",
      portal_url: "https://example.gov/service",
      created_at: "2026-01-01T12:00:00Z",
      updated_at: "2026-01-01T12:00:00Z",
    },
  ],
  summary: {
    total: 1,
    by_source: { govdata: 1 },
    by_pipeline_stage: { T3: 1 },
  },
  total: 1,
  offset: 0,
  limit: 50,
};

const coverageResponse = {
  by_source: { govdata: 3 },
  tasks_pending: 2,
  tasks_failed: 1,
  emit_ready_count: 3,
  task_counts: { total: 3, pending: 2, claimed: 0, completed: 0, failed: 1 },
  task_counts_by_kind: {},
  candidates: { total: 0, staged: 0, emitted: 0, mentions: 0 },
  llm_outcomes: { extracted: 0, no_documents: 0, login_wall: 0, no_content: 0 },
  artifacts: { by_kind: {}, total_bytes: 0, bytes_cap: 8589934592 },
  fetch_attempts_total: 0,
  stale_claims: 0,
  stale_runs: 0,
  failures_by_source: {},
  last_successful_run: null,
};

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function stubDiscoveryFetch(
  responses: {
    catalogue?: Response | (() => Response);
    coverage?: Response | (() => Response);
  } = {},
) {
  const fetchMock = vi.fn(async (input?: unknown) => {
    const url = new URL(String(input));

    if (url.pathname.endsWith("/api/v1/me")) {
      return new Response(
        JSON.stringify({
          id: "user-1",
          email: session.email,
          display_name: null,
          role: "user",
        }),
      );
    }
    if (url.pathname.endsWith("/api/v1/translations")) {
      return new Response(JSON.stringify({ translations: {} }));
    }

    const response = url.pathname.endsWith("/catalogue")
      ? responses.catalogue
      : responses.coverage;

    if (typeof response === "function") return response();
    if (response) return response;
    return new Response("", { status: 503 });
  });

  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderCataloguePage(entry = "/admin/discovery/catalogue") {
  return renderWithProviders(<DiscoveryCataloguePage />, {
    authGateway: createFakeAuthGateway({ session }),
    initialEntries: [entry],
  });
}

it("DiscoveryCataloguePage · renders coverage tables and catalogue rows after both requests succeed", async () => {
  stubDiscoveryFetch({
    catalogue: new Response(JSON.stringify(catalogueResponse)),
    coverage: new Response(JSON.stringify(coverageResponse)),
  });

  renderCataloguePage();

  expect(
    await screen.findByRole("table", { name: "Catalogue services" }),
  ).toHaveTextContent("service-1");
  const queue = screen.getByRole("table", { name: "Task queue" });
  expect(
    within(queue).getByRole("row", { name: "Pending tasks 2" }),
  ).toBeVisible();
  expect(
    within(queue).getByRole("row", { name: "Emit-ready 3" }),
  ).toBeVisible();
  expect(
    within(
      screen.getByRole("table", { name: "Catalogue rows by source" }),
    ).getByRole("row", { name: "govdata 3" }),
  ).toBeVisible();
});

it("DiscoveryCataloguePage · keeps catalogue rows visible when coverage fails", async () => {
  const fetchMock = stubDiscoveryFetch({
    catalogue: () => new Response(JSON.stringify(catalogueResponse)),
    coverage: () => new Response("", { status: 500 }),
  });

  const { user } = renderCataloguePage();

  expect(
    await screen.findByRole("table", { name: "Catalogue services" }),
  ).toHaveTextContent("service-1");
  const retryButton = await screen.findByRole("button", { name: "Try again" });
  expect(retryButton).toBeInTheDocument();

  const coverageCallsBeforeRetry = fetchMock.mock.calls.filter(([input]) =>
    String(input).includes("/api/v1/discovery/admin/coverage"),
  ).length;
  const catalogueCallsBeforeRetry = fetchMock.mock.calls.filter(([input]) =>
    String(input).includes("/api/v1/discovery/admin/catalogue"),
  ).length;
  await user.click(retryButton);
  await waitFor(() =>
    expect(
      fetchMock.mock.calls.filter(([input]) =>
        String(input).includes("/api/v1/discovery/admin/coverage"),
      ),
    ).toHaveLength(coverageCallsBeforeRetry + 1),
  );
  expect(
    fetchMock.mock.calls.filter(([input]) =>
      String(input).includes("/api/v1/discovery/admin/catalogue"),
    ),
  ).toHaveLength(catalogueCallsBeforeRetry);
});

it("DiscoveryCataloguePage · shows a retryable state when catalogue loading fails", async () => {
  const fetchMock = stubDiscoveryFetch({
    catalogue: () => new Response("", { status: 500 }),
    coverage: () => new Response(JSON.stringify(coverageResponse)),
  });

  renderCataloguePage();

  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Try again" }),
    ).toBeInTheDocument(),
  );
  expect(screen.queryByText("service-1")).not.toBeInTheDocument();
  expect(screen.getByRole("table", { name: "Task queue" })).toBeVisible();
  expect(
    fetchMock.mock.calls.some(([input]) =>
      String(input).includes("/api/v1/discovery/admin/catalogue"),
    ),
  ).toBe(true);
});

it("DiscoveryCataloguePage · shows a deliberate empty state for zero catalogue rows", async () => {
  stubDiscoveryFetch({
    catalogue: new Response(
      JSON.stringify({ ...catalogueResponse, items: [], total: 0 }),
    ),
    coverage: new Response(JSON.stringify(coverageResponse)),
  });

  renderCataloguePage();

  expect(await screen.findByText("No catalogue services")).toBeInTheDocument();
  expect(screen.getByRole("table", { name: "Task queue" })).toBeVisible();
});

it("DiscoveryCataloguePage · keeps its existing rows inside the section shell", async () => {
  stubDiscoveryFetch({
    catalogue: new Response(JSON.stringify(catalogueResponse)),
    coverage: new Response(JSON.stringify(coverageResponse)),
  });

  renderCataloguePage();

  const table = await screen.findByRole("table", {
    name: "Catalogue services",
  });
  const shell = table.closest("[data-section-card]");

  expect(shell).not.toBeNull();
  expect(shell).toHaveTextContent("service-1");
  expect(getComputedStyle(shell!).boxShadow).toBe(
    "var(--chakra-shadows-shell)",
  );
});

it("DiscoveryCataloguePage · a failed catalogue query keeps search and filters reachable", async () => {
  stubDiscoveryFetch({
    catalogue: () => new Response("", { status: 500 }),
    coverage: () => new Response(JSON.stringify(coverageResponse)),
  });

  renderCataloguePage();

  const table = await screen.findByRole("table", {
    name: "Catalogue services",
  });
  expect(
    within(table).getByRole("button", { name: "Try again" }),
  ).toBeVisible();
  expect(within(table).queryByRole("link")).not.toBeInTheDocument();
  expect(
    within(table).getByRole("button", { name: "Catalogue source" }),
  ).toBeVisible();
  expect(
    screen.getByRole("textbox", { name: "Search external IDs" }),
  ).toBeVisible();
});

function catalogueUrls(total = 120) {
  stubDiscoveryFetch({
    catalogue: () =>
      new Response(JSON.stringify({ ...catalogueResponse, total, limit: 20 })),
    coverage: () => new Response(JSON.stringify(coverageResponse)),
  });
  const fetchMock = vi.mocked(fetch);
  return () =>
    fetchMock.mock.calls
      .map(([input]) => new URL(String(input)))
      .filter((url) => url.pathname.endsWith("/discovery/admin/catalogue"))
      .slice(-1)[0];
}

it("DiscoveryCataloguePage · pages past the first page of the response total", async () => {
  const lastRequest = catalogueUrls();
  const { user } = renderCataloguePage(
    "/admin/discovery/catalogue?sort_by=stage",
  );

  expect(await screen.findByText("120 catalogue services")).toBeVisible();
  expect(lastRequest().searchParams.get("limit")).toBe("20");
  await user.click(screen.getByRole("button", { name: "Next page" }));

  await waitFor(() =>
    expect(lastRequest().searchParams.get("offset")).toBe("20"),
  );
  expect(lastRequest().searchParams.get("sort_by")).toBe("stage");
});

it("DiscoveryCataloguePage · sort, filter and search return to page one and serialize the contract", async () => {
  const lastRequest = catalogueUrls();
  const { user } = renderCataloguePage("/admin/discovery/catalogue?offset=40");
  await screen.findByText("120 catalogue services");

  await user.click(screen.getByRole("button", { name: "External ID" }));
  await waitFor(() =>
    expect(lastRequest().searchParams.get("sort_by")).toBe("external_id"),
  );
  expect(lastRequest().searchParams.get("sort_order")).toBe("asc");
  expect(lastRequest().searchParams.get("offset")).toBe("0");

  await user.click(screen.getByRole("button", { name: "Catalogue source" }));
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Catalogue source" }),
    "pvog",
  );
  await user.click(screen.getByRole("button", { name: "Apply" }));
  await waitFor(() =>
    expect(lastRequest().searchParams.get("filter[source]")).toBe("pvog"),
  );
  expect(lastRequest().searchParams.get("sort_by")).toBe("external_id");

  await user.type(
    screen.getByRole("textbox", { name: "Search external IDs" }),
    "svc",
  );
  await user.click(screen.getByRole("button", { name: "Search" }));
  await waitFor(() => expect(lastRequest().searchParams.get("q")).toBe("svc"));

  await user.click(screen.getByRole("button", { name: "Clear all filters" }));
  await waitFor(() =>
    expect(lastRequest().searchParams.has("filter[source]")).toBe(false),
  );
  expect(lastRequest().searchParams.get("q")).toBe("svc");
});

it("DiscoveryCataloguePage · invalid URL list state falls back to safe defaults", async () => {
  const lastRequest = catalogueUrls();
  renderCataloguePage(
    "/admin/discovery/catalogue?offset=abc&limit=0&sort_by=raw_payload&filter[source]=nowhere&filter[stage]=T0",
  );
  await screen.findByText("120 catalogue services");

  const params = lastRequest().searchParams;
  expect(params.get("offset")).toBe("0");
  expect(params.get("limit")).toBe("20");
  for (const key of ["sort_by", "filter[source]", "filter[stage]"]) {
    expect(params.has(key)).toBe(false);
  }
});

it("DiscoveryCataloguePage · a single page of rows shows no pagination", async () => {
  catalogueUrls(1);
  renderCataloguePage();

  expect(await screen.findByText("1 catalogue service")).toBeVisible();
  expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
});
