import { screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import { createFakeAuthGateway } from "../../auth/services/fakeAuthGateway";
import type { AuthSession } from "../../auth/services/authGateway";
import DiscoveryTasksPage from "./DiscoveryTasksPage";

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

  const table = await screen.findByRole("table");
  expect(table).toHaveTextContent("https://example.gov/service");
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

it("DiscoveryTasksPage · sends the selected kind as a query parameter", async () => {
  const urls = stubEmptyTasks();

  const { user } = renderWithProviders(<DiscoveryTasksPage />, {
    authGateway: createFakeAuthGateway({ session }),
  });
  await waitFor(() => expect(urls.length).toBeGreaterThan(0));
  expect(urls[0].searchParams.has("kind")).toBe(false);

  await user.selectOptions(
    screen.getByLabelText("Task kind"),
    "harvest_payload",
  );

  await waitFor(() =>
    expect(urls.at(-1)?.searchParams.get("kind")).toBe("harvest_payload"),
  );
  await user.selectOptions(screen.getByLabelText("Task kind"), "");
  await waitFor(() =>
    expect(urls.at(-1)?.searchParams.has("kind")).toBe(false),
  );
});

it("DiscoveryTasksPage · lists the browser kinds in the kind select and filters by render_page", async () => {
  const urls = stubEmptyTasks();

  const { user } = renderWithProviders(<DiscoveryTasksPage />, {
    authGateway: createFakeAuthGateway({ session }),
  });
  await waitFor(() => expect(urls.length).toBeGreaterThan(0));
  const select = screen.getByLabelText("Task kind");

  expect(
    within(select).getByRole("option", { name: "capture_screenshot" }),
  ).toBeInTheDocument();
  await user.selectOptions(select, "render_page");

  await waitFor(() =>
    expect(urls.at(-1)?.searchParams.get("kind")).toBe("render_page"),
  );
});

it("DiscoveryTasksPage · offers llm_extract in the kind select and filters by it", async () => {
  const urls = stubEmptyTasks();

  const { user } = renderWithProviders(<DiscoveryTasksPage />, {
    authGateway: createFakeAuthGateway({ session }),
  });
  await waitFor(() => expect(urls.length).toBeGreaterThan(0));
  await user.selectOptions(screen.getByLabelText("Task kind"), "llm_extract");

  await waitFor(() =>
    expect(urls.at(-1)?.searchParams.get("kind")).toBe("llm_extract"),
  );
});

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

  const table = await screen.findByRole("table");
  expect(within(table).getByText("render_pdf_v2")).toBeInTheDocument();
});
