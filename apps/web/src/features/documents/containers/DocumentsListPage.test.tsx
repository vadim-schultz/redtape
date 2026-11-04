import { screen, waitFor } from "@testing-library/react";
import { useLocation } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import {
  candidateFixture,
  candidatePage,
} from "../../../test/candidateFixtures";
import {
  json,
  listCalls,
  stubCandidatesApi,
} from "../../../test/candidatesApiStub";
import { renderWithProviders } from "../../../test/renderWithProviders";
import DocumentsListPage from "./DocumentsListPage";

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function Search() {
  return <output data-testid="search">{useLocation().search}</output>;
}

function renderAt(url: string) {
  return renderWithProviders(
    <>
      <DocumentsListPage />
      <Search />
    </>,
    { initialEntries: [url] },
  );
}

function stubPage() {
  return stubCandidatesApi(() =>
    json(candidatePage([candidateFixture({ categories: [] })])),
  );
}

it("DocumentsListPage · search renders before secondary category browsing", async () => {
  stubPage();
  renderAt("/documents");

  const search = await screen.findByRole("textbox", {
    name: "Search document titles",
  });
  const categoryHeading = await screen.findByText("Categories");

  expect(
    Boolean(
      search.compareDocumentPosition(categoryHeading) &
      Node.DOCUMENT_POSITION_FOLLOWING,
    ),
  ).toBe(true);
});

it("category filter · selecting a root sends one canonical category code", async () => {
  const fetchMock = stubPage();
  const { user } = renderAt("/documents");

  await user.click(await screen.findByRole("button", { name: "Identity" }));

  expect(screen.getByTestId("search")).toHaveTextContent(
    "?category=identity-and-documents",
  );
  await waitFor(() =>
    expect(
      listCalls(fetchMock).at(-1)?.searchParams.get("filter[category]"),
    ).toBe("identity-and-documents"),
  );
});

it("legacy URL · old axis parameters are not silently widened to an unfiltered request", async () => {
  const fetchMock = stubPage();
  renderAt("/documents?domain=identity");

  await screen.findByRole("link", { name: /Passport/ });

  expect(listCalls(fetchMock).at(-1)?.searchParams.get("filter[domain]")).toBe(
    "identity",
  );
});

it("category filter · unknown URL category does not select a root", async () => {
  const fetchMock = stubPage();
  renderAt("/documents?category=ghost");

  await screen.findByRole("link", { name: /Passport/ });

  expect(screen.getByRole("button", { name: "Identity" })).toHaveAttribute(
    "aria-pressed",
    "false",
  );
  expect(
    listCalls(fetchMock).at(-1)?.searchParams.has("filter[category]"),
  ).toBe(false);
});
