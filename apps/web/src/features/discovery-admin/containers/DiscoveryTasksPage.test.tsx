import { screen, waitFor, within } from "@testing-library/react";
import { focusManager } from "@tanstack/react-query";
import type userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import { createFakeAuthGateway } from "../../auth/services/fakeAuthGateway";
import type { AuthSession } from "../../auth/services/authGateway";
import DiscoveryTasksPage from "./DiscoveryTasksPage";

type User = ReturnType<typeof userEvent.setup>;

const session: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "admin@example.com",
};

const adminTasksUrl = "/api/v1/discovery/admin/tasks";

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function stubTasksFetch(handler: (url: URL) => Response | Promise<Response>) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input?: unknown) => {
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
      if (url.pathname.endsWith(adminTasksUrl)) {
        return handler(url);
      }
      return new Response("", { status: 503 });
    }),
  );
}

it("DiscoveryTasksPage · renders rows from mocked admin tasks API", async () => {
  stubTasksFetch(
    () =>
      new Response(
        JSON.stringify({
          items: [
            {
              id: "task-1",
              catalogue_service_id: "cat-1",
              source: "govdata",
              kind: "fetch_url",
              target_url: "https://example.gov/service",
              status: "pending",
              priority: 100,
              attempt_count: 0,
              not_before: null,
              input_key: null,
              lease_expires_at: null,
              created_at: "2026-01-01T12:00:00Z",
              updated_at: "2026-01-01T12:00:00Z",
            },
          ],
          total: 1,
          offset: 0,
          limit: 20,
        }),
      ),
  );

  renderWithProviders(<DiscoveryTasksPage />, {
    authGateway: createFakeAuthGateway({ session }),
  });

  const table = screen.getByRole("table");
  expect(
    await within(table).findByText("https://example.gov/service"),
  ).toBeVisible();
  expect(table).toHaveTextContent("pending");
  expect(table).toHaveTextContent("govdata");
});

it("DiscoveryTasksPage · shows error state when query fails", async () => {
  stubTasksFetch(() => new Response("", { status: 500 }));

  renderWithProviders(<DiscoveryTasksPage />, {
    authGateway: createFakeAuthGateway({ session }),
  });

  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Try again" }),
    ).toBeInTheDocument(),
  );
});

function stubEmptyTasks() {
  const urls: URL[] = [];
  stubTasksFetch((url) => {
    urls.push(url);
    return new Response(
      JSON.stringify({ items: [], total: 0, offset: 0, limit: 20 }),
    );
  });
  return urls;
}

it("DiscoveryTasksPage · tolerates an unknown future kind label", async () => {
  stubTasksFetch(
    () =>
      new Response(
        JSON.stringify({
          items: [
            {
              id: "task-9",
              catalogue_service_id: "cat-1",
              source: "pvog",
              kind: "render_pdf_v2",
              target_url: "https://example.gov/pdf",
              status: "pending",
              priority: 100,
              attempt_count: 0,
              not_before: null,
              input_key: null,
              lease_expires_at: null,
              created_at: "2026-01-01T12:00:00Z",
              updated_at: "2026-01-01T12:00:00Z",
            },
          ],
          total: 1,
          offset: 0,
          limit: 20,
        }),
      ),
  );

  renderWithProviders(<DiscoveryTasksPage />, {
    authGateway: createFakeAuthGateway({ session }),
  });

  const table = screen.getByRole("table");
  expect(await within(table).findByText("render_pdf_v2")).toBeInTheDocument();
});

function taskItem(id: string) {
  return {
    id,
    catalogue_service_id: "cat-1",
    source: "govdata",
    kind: "fetch_url",
    target_url: `https://example.gov/${id}`,
    status: "pending",
    priority: 100,
    attempt_count: 0,
    not_before: null,
    input_key: null,
    lease_expires_at: null,
    created_at: "2026-01-01T12:00:00Z",
    updated_at: "2026-01-01T12:00:00Z",
  };
}

function stubPagedTasks(total = 45) {
  const urls: URL[] = [];
  stubTasksFetch((url) => {
    urls.push(url);
    return new Response(
      JSON.stringify({
        items: [taskItem("a"), taskItem("b")],
        total,
        offset: Number(url.searchParams.get("offset") ?? 0),
        limit: 20,
      }),
    );
  });
  return urls;
}

function renderPage(entry = "/admin/discovery/tasks") {
  return renderWithProviders(<DiscoveryTasksPage />, {
    authGateway: createFakeAuthGateway({ session }),
    initialEntries: [entry],
  });
}

async function applyFilter(user: User, label: string, value: string) {
  await user.click(screen.getByRole("button", { name: label }));
  await user.selectOptions(
    screen.getByRole("combobox", { name: label }),
    value,
  );
  await user.click(screen.getByRole("button", { name: "Apply" }));
}

const lastUrl = (urls: URL[]) => urls[urls.length - 1];

it("changing a filter resets the admin table to the first page", async () => {
  const urls = stubPagedTasks();
  const { user } = renderPage("/admin/discovery/tasks?offset=20&sort_by=kind");
  await screen.findByText("21–40 of 45");
  expect(lastUrl(urls).searchParams.get("offset")).toBe("20");

  await applyFilter(user, "Task kind", "llm_extract");

  await waitFor(() =>
    expect(lastUrl(urls).searchParams.get("filter[kind]")).toBe("llm_extract"),
  );
  const params = lastUrl(urls).searchParams;
  expect(params.get("offset")).toBe("0");
  expect(params.get("sort_by")).toBe("kind");
  expect(screen.getByText("Task kind: llm_extract")).toBeVisible();
});

it("changing sort resets the admin table and serializes direction", async () => {
  const urls = stubPagedTasks();
  const { user } = renderPage("/admin/discovery/tasks?offset=20");
  await screen.findByText("21–40 of 45");

  await user.click(screen.getByRole("button", { name: "Attempts" }));
  await waitFor(() =>
    expect(lastUrl(urls).searchParams.get("sort_by")).toBe("attempts"),
  );
  expect(lastUrl(urls).searchParams.get("sort_order")).toBe("asc");
  expect(lastUrl(urls).searchParams.get("offset")).toBe("0");

  await user.click(screen.getByRole("button", { name: "Attempts" }));
  await waitFor(() =>
    expect(lastUrl(urls).searchParams.get("sort_order")).toBe("desc"),
  );
});

it("clearing filters restores the default result set", async () => {
  const urls = stubPagedTasks();
  const { user } = renderPage(
    "/admin/discovery/tasks?offset=20&filter[status]=failed&filter[kind]=fetch_url",
  );
  expect(await screen.findByText("Task status: failed")).toBeVisible();
  await waitFor(() => expect(urls.length).toBeGreaterThan(0));
  expect(lastUrl(urls).searchParams.get("filter[status]")).toBe("failed");

  await user.click(screen.getByRole("button", { name: "Clear all filters" }));

  await waitFor(() =>
    expect(lastUrl(urls).searchParams.has("filter[status]")).toBe(false),
  );
  const params = lastUrl(urls).searchParams;
  expect(params.has("filter[kind]")).toBe(false);
  expect(params.get("offset")).toBe("0");
  expect(screen.queryByText(/Task status:/)).not.toBeInTheDocument();
});

it("removing one applied filter keeps the others", async () => {
  const urls = stubPagedTasks();
  const { user } = renderPage(
    "/admin/discovery/tasks?filter[status]=failed&filter[kind]=fetch_url",
  );
  await screen.findByText("Task status: failed");

  await user.click(
    screen.getByRole("button", { name: "Remove filter Task status" }),
  );

  await waitFor(() =>
    expect(lastUrl(urls).searchParams.has("filter[status]")).toBe(false),
  );
  expect(lastUrl(urls).searchParams.get("filter[kind]")).toBe("fetch_url");
});

it("invalid URL list state falls back to safe defaults", async () => {
  const urls = stubPagedTasks();
  renderPage(
    "/admin/discovery/tasks?offset=-5&limit=9999&sort_by=password&sort_order=up&filter[status]=gone&filter[priority]=1&q=",
  );
  await screen.findByText("45 tasks");

  const params = urls[0].searchParams;
  expect(params.get("offset")).toBe("0");
  expect(params.get("limit")).toBe("20");
  for (const key of [
    "sort_by",
    "sort_order",
    "filter[status]",
    "filter[priority]",
    "q",
  ]) {
    expect(params.has(key)).toBe(false);
  }
});

it("a search term resets the page and is sent as q", async () => {
  const urls = stubPagedTasks();
  const { user } = renderPage("/admin/discovery/tasks?offset=20");
  await screen.findByText("21–40 of 45");

  await user.type(
    screen.getByRole("textbox", { name: "Search target URLs" }),
    "gov",
  );
  await user.click(screen.getByRole("button", { name: "Search" }));

  await waitFor(() => expect(lastUrl(urls).searchParams.get("q")).toBe("gov"));
  expect(lastUrl(urls).searchParams.get("offset")).toBe("0");
});

it("paging keeps the sort and filters of the query", async () => {
  const urls = stubPagedTasks();
  const { user } = renderPage(
    "/admin/discovery/tasks?sort_by=kind&filter[source]=pvog",
  );
  await screen.findByText("45 tasks");

  await user.click(screen.getByRole("button", { name: "Next page" }));

  await waitFor(() =>
    expect(lastUrl(urls).searchParams.get("offset")).toBe("20"),
  );
  expect(lastUrl(urls).searchParams.get("sort_by")).toBe("kind");
  expect(lastUrl(urls).searchParams.get("filter[source]")).toBe("pvog");
});

it("single-page result hides pagination controls", async () => {
  stubPagedTasks(2);
  renderPage();

  expect(await screen.findByText("2 tasks")).toBeInTheDocument();
  expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
});

it("shows the empty state and hides paging without stale rows", async () => {
  stubEmptyTasks();
  renderPage();

  expect(await screen.findByText("No tasks in queue")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Next page" })).toBeNull();
});

it("refetch failure preserves previous rows with visible feedback", async () => {
  let fail = false;
  stubTasksFetch(() =>
    fail
      ? new Response("", { status: 500 })
      : new Response(
          JSON.stringify({
            items: [taskItem("a")],
            total: 1,
            offset: 0,
            limit: 20,
          }),
        ),
  );
  const { user } = renderPage();
  expect(await screen.findByText("https://example.gov/a")).toBeVisible();

  fail = true;
  focusManager.setFocused(false);
  focusManager.setFocused(true);

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Could not refresh",
  );
  expect(screen.getByText("https://example.gov/a")).toBeVisible();
  fail = false;
  await user.click(screen.getByRole("button", { name: "Try again" }));
  await waitFor(() =>
    expect(screen.queryByRole("alert")).not.toBeInTheDocument(),
  );
  expect(screen.getByText("https://example.gov/a")).toBeVisible();
});
