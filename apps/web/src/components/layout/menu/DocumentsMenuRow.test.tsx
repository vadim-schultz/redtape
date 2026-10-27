import { screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { createFakeAuthGateway } from "../../../features/auth/services/fakeAuthGateway";
import type { AuthSession } from "../../../features/auth/services/authGateway";
import { renderWithProviders } from "../../../test/renderWithProviders";
import DocumentsMenuRow from "./DocumentsMenuRow";

vi.mock("../../../app/retryPolicy", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../../app/retryPolicy")>()),
  retryDelay: () => 0,
}));

const session: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "admin@example.com",
};

const adminTasksUrl = "/api/v1/discovery/admin/tasks";

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function stubFetch(adminStatus: number) {
  const fetchMock = vi.fn(async (input?: unknown) => {
    const url = String(input);
    if (url.includes(adminTasksUrl) && adminStatus === 200) {
      return new Response(
        JSON.stringify({ items: [], total: 0, offset: 0, limit: 1 }),
      );
    }
    return new Response("", { status: adminStatus });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderRow(adminStatus: number) {
  const fetchMock = stubFetch(adminStatus);
  renderWithProviders(<DocumentsMenuRow />, {
    authGateway: createFakeAuthGateway({ session }),
  });
  return fetchMock;
}

function rowOf(link: HTMLElement): HTMLElement {
  return link.parentElement as HTMLElement;
}

it("documents menu row renders browse suggest and discovery links in one container", async () => {
  renderRow(200);

  await screen.findByRole("link", { name: "Tasks" });

  const links = screen.getAllByRole("link");
  expect(links).toHaveLength(6);
  expect(new Set(links.map(rowOf)).size).toBe(1);
  expect(rowOf(links[0]).children).toHaveLength(6);
});

it("documents menu row links the admin documents list as the sixth icon in the same row", async () => {
  renderRow(200);

  const link = await screen.findByRole("link", { name: "Documents" });

  expect(link).toHaveAttribute("href", "/admin/discovery/documents");
  expect(rowOf(link)).toBe(rowOf(screen.getByRole("link", { name: "Tasks" })));
  expect(link.textContent).toBe("");
});

it("documents menu row renders only browse and suggest when the discovery probe is hidden", async () => {
  const fetchMock = renderRow(403);

  await waitFor(() => expect(fetchMock).toHaveBeenCalled());
  const links = screen.getAllByRole("link");
  expect(screen.queryByText("Discovery unavailable")).toBeNull();
  expect(links).toHaveLength(2);
  expect(rowOf(links[0]).children).toHaveLength(2);
  expect(rowOf(rowOf(links[0]))).toBe(screen.getByTestId("key-value-row"));
});

it("documents menu row keeps the unavailable hint in the same row", async () => {
  renderRow(503);

  const hint = await screen.findByText("Discovery unavailable");

  const links = screen.getAllByRole("link");
  expect(links).toHaveLength(2);
  expect(rowOf(hint)).toBe(rowOf(links[0]));
  expect(rowOf(links[1])).toBe(rowOf(links[0]));
});

it("every link keeps its aria-label and title", async () => {
  renderRow(200);

  await screen.findByRole("link", { name: "Tasks" });

  const names = [
    "Browse Documents",
    "Suggest",
    "Catalogue",
    "Coverage",
    "Tasks",
    "Documents",
  ];
  for (const name of names) {
    expect(screen.getByRole("link", { name })).toHaveAttribute("title", name);
  }
});
