import { screen, waitFor } from "@testing-library/react";
import { useLocation } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { candidateFixture } from "../../../test/candidateFixtures";
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

function respondWith(
  documents: unknown[],
  taxonomyStatus = 200,
  total = documents.length,
) {
  fetchMock.mockImplementation(async (url: string) => {
    const path = new URL(String(url)).pathname;
    if (path.endsWith("/api/v1/candidates"))
      return new Response(
        JSON.stringify({ items: documents, total, offset: 0, limit: 20 }),
      );
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
    .filter((url) => url.pathname.endsWith("/api/v1/candidates"));
}

const passport = candidateFixture({ id: "1", title: "Passport" });

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  respondWith([passport]);
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

it("DocumentsListPage · passes the URL filters to the candidate API as CSV", async () => {
  renderWithProviders(<DocumentsListPage />, {
    initialEntries: ["/documents?domain=d1&domain=d2&situation=s2"],
  });

  await waitFor(() => expect(documentsCalls()).not.toHaveLength(0));

  const params = documentsCalls()[0].searchParams;
  expect(params.get("filter[domain]")).toBe("d1,d2");
  expect(params.get("filter[situation]")).toBe("s2");
});

it("DocumentsListPage · without chips no filter reaches the API", async () => {
  renderWithProviders(<DocumentsListPage />);

  await waitFor(() => expect(documentsCalls()).not.toHaveLength(0));

  const names = [...documentsCalls()[0].searchParams.keys()];
  expect(names.filter((name) => name.startsWith("filter["))).toEqual([]);
});

it("DocumentsListPage · toggling a chip refetches with the new filter", async () => {
  const { user } = renderWithProviders(<DocumentsListPage />);

  await user.click(await screen.findByRole("button", { name: "D1" }));

  await waitFor(() =>
    expect(documentsCalls().at(-1)?.searchParams.get("filter[domain]")).toBe(
      "d1",
    ),
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
  respondWith([passport], 500);
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

it("DocumentsListPage · cards link to the candidate item page", async () => {
  renderWithProviders(<DocumentsListPage />);

  const link = await screen.findByRole("link", { name: /Passport/ });

  expect(link).toHaveAttribute("href", "/candidates/1");
});

it("DocumentsListPage · the count is the full result, not the page", async () => {
  respondWith([passport], 200, 57);
  renderWithProviders(<DocumentsListPage />);

  expect(await screen.findByTestId("query-status-count")).toHaveTextContent(
    "57 documents",
  );
});

it("DocumentsListPage · has no municipality picker and no leaf facet", async () => {
  renderWithProviders(<DocumentsListPage />);

  await screen.findByRole("link", { name: /Passport/ });

  expect(screen.queryByText(/municipality|state|district/i)).toBeNull();
  expect(documentsCalls()[0].searchParams.has("municipality_code")).toBe(false);
});

function Search() {
  return <p data-testid="search">{useLocation().search}</p>;
}

it("DocumentsListPage · toggling a chip returns to the first page", async () => {
  const { user } = renderWithProviders(
    <>
      <DocumentsListPage />
      <Search />
    </>,
    { initialEntries: ["/documents?offset=40&q=pass"] },
  );

  await user.click(await screen.findByRole("button", { name: "D1" }));

  const search = new URLSearchParams(screen.getByTestId("search").textContent);
  expect(search.has("offset")).toBe(false);
  expect(search.get("domain")).toBe("d1");
  expect(search.get("q")).toBe("pass");
});
