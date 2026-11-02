import { screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { expandControlsBesideCount } from "../../../test/queryStatusCountRow";
import { renderWithProviders } from "../../../test/renderWithProviders";
import DocumentsListPage from "./DocumentsListPage";

const fetchMock = vi.fn();

const terms = (codes: string[]) =>
  codes.map((code) => ({
    code,
    name: code.toUpperCase(),
    description: "",
    icon: null,
  }));

function respondWith(documents: unknown[], taxonomyStatus = 200) {
  fetchMock.mockImplementation(async (url: string) => {
    const path = new URL(String(url)).pathname;
    if (path.endsWith("/api/v1/documents"))
      return new Response(JSON.stringify({ items: documents, total: 0 }));
    if (path.endsWith("/domains"))
      return new Response(JSON.stringify(terms(["d1", "d2"])), {
        status: taxonomyStatus,
      });
    if (path.endsWith("/life-situation-groups"))
      return new Response(JSON.stringify(terms(["g1"])), {
        status: taxonomyStatus,
      });
    if (path.endsWith("/life-situations"))
      return new Response(
        JSON.stringify(
          terms(["s1", "s2"]).map((term) => ({ ...term, group_code: "g1" })),
        ),
        { status: taxonomyStatus },
      );
    return new Response(JSON.stringify({ items: [] }));
  });
}

function pressed(name: string) {
  return screen.findByRole("button", { name, pressed: true });
}

function documentsCalls(): URL[] {
  return fetchMock.mock.calls
    .map(([url]) => new URL(String(url)))
    .filter((url) => url.pathname.endsWith("/api/v1/documents"));
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  respondWith([{ id: "1", slug: "one", title: "Passport" }]);
});
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

it("DocumentsListPage · /documents?situation=X shows only the situation chip pressed", async () => {
  renderWithProviders(<DocumentsListPage />, {
    initialEntries: ["/documents?situation=s1"],
  });

  await pressed("S1");

  expect(screen.getAllByRole("button", { pressed: true })).toHaveLength(1);
});

it("DocumentsListPage · /documents?domain=D shows only the domain chip pressed", async () => {
  renderWithProviders(<DocumentsListPage />, {
    initialEntries: ["/documents?domain=d2"],
  });

  await pressed("D2");

  expect(screen.getAllByRole("button", { pressed: true })).toHaveLength(1);
});

it("DocumentsListPage · passes the URL filters to the documents API", async () => {
  renderWithProviders(<DocumentsListPage />, {
    initialEntries: ["/documents?domain=d1&situation=s2"],
  });

  await waitFor(() => expect(documentsCalls()).not.toHaveLength(0));

  const params = documentsCalls()[0].searchParams;
  expect(params.getAll("domain")).toEqual(["d1"]);
  expect(params.getAll("situation")).toEqual(["s2"]);
});

it("DocumentsListPage · toggling a chip refetches with the new filter", async () => {
  const { user } = renderWithProviders(<DocumentsListPage />);

  await user.click(await screen.findByRole("button", { name: "D1" }));

  await waitFor(() =>
    expect(documentsCalls().at(-1)?.searchParams.getAll("domain")).toEqual([
      "d1",
    ]),
  );
});

it("DocumentsListPage · empty filtered result renders the empty state", async () => {
  respondWith([]);
  renderWithProviders(<DocumentsListPage />, {
    initialEntries: ["/documents?domain=d1"],
  });

  expect(await screen.findByText(/no documents found/i)).toBeInTheDocument();
});

it("DocumentsListPage · taxonomy failure keeps the list usable", async () => {
  respondWith([{ id: "1", slug: "one", title: "Passport" }], 500);
  renderWithProviders(<DocumentsListPage />);

  expect(await screen.findByText("Passport")).toBeInTheDocument();
});

it("DocumentsListPage · populated document count row has no expand control", async () => {
  renderWithProviders(<DocumentsListPage />, {
    initialEntries: ["/documents"],
  });

  const count = await screen.findByTestId("query-status-count");
  expect(count).toHaveTextContent("1 document");
  expect(expandControlsBesideCount(count)).toHaveLength(0);
  expect(count.closest("[aria-expanded]")).toBeNull();
  expect(screen.getByRole("link", { name: /Passport/ })).toBeVisible();
});
