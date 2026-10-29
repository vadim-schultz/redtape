import { screen, waitFor } from "@testing-library/react";
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

function renderCataloguePage() {
  return renderWithProviders(<DiscoveryCataloguePage />, {
    authGateway: createFakeAuthGateway({ session }),
  });
}

it("DiscoveryCataloguePage · renders coverage chips and catalogue rows after both requests succeed", async () => {
  stubDiscoveryFetch({
    catalogue: new Response(JSON.stringify(catalogueResponse)),
    coverage: new Response(JSON.stringify(coverageResponse)),
  });

  renderCataloguePage();

  expect(await screen.findByRole("table")).toHaveTextContent("service-1");
  expect(screen.getByText("govdata: 3")).toBeInTheDocument();
  expect(screen.getByText("Pending tasks: 2")).toBeInTheDocument();
  expect(screen.getByText("Emit-ready: 3")).toBeInTheDocument();
});

it("DiscoveryCataloguePage · keeps catalogue rows visible when coverage fails", async () => {
  const fetchMock = stubDiscoveryFetch({
    catalogue: () => new Response(JSON.stringify(catalogueResponse)),
    coverage: () => new Response("", { status: 500 }),
  });

  const { user } = renderCataloguePage();

  expect(await screen.findByRole("table")).toHaveTextContent("service-1");
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
  expect(screen.getByText("govdata: 3")).toBeInTheDocument();
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

  expect(
    await screen.findByText("No catalogue services yet."),
  ).toBeInTheDocument();
  expect(screen.getByText("govdata: 3")).toBeInTheDocument();
});

it("DiscoveryCataloguePage · keeps its existing rows inside the section shell", async () => {
  stubDiscoveryFetch({
    catalogue: new Response(JSON.stringify(catalogueResponse)),
    coverage: new Response(JSON.stringify(coverageResponse)),
  });

  renderCataloguePage();

  const table = await screen.findByRole("table");
  const shell = table.closest("[data-section-card]");

  expect(shell).not.toBeNull();
  expect(shell).toHaveTextContent("service-1");
  expect(getComputedStyle(shell!).boxShadow).toBe(
    "var(--chakra-shadows-shell)",
  );
});

it("DiscoveryCataloguePage · a failed catalogue query shows no shell around the error", async () => {
  stubDiscoveryFetch({
    catalogue: () => new Response("", { status: 500 }),
    coverage: () => new Response(JSON.stringify(coverageResponse)),
  });

  renderCataloguePage();

  const retry = await screen.findByRole("button", { name: "Try again" });

  expect(retry.closest("[data-section-card]")).toBeNull();
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
});
