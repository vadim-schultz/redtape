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

it("DocumentsListPage · a hybrid response shows both rings and no keyword hint", async () => {
  stubCandidatesApi(() =>
    json({
      ...candidatePage([candidateFixture({ similarity: 0.66 })]),
      search_mode: "hybrid",
    }),
  );
  renderAt("/documents?q=passport");

  expect(
    await screen.findByRole("progressbar", { name: /^Similarity 66%/ }),
  ).toBeInTheDocument();
  expect(screen.getByText("1 result")).toBeInTheDocument();
  expect(screen.queryByText(/Semantic matching is unavailable/)).toBeNull();
});

it("DocumentsListPage · a keyword response hints once and draws no similarity ring", async () => {
  stubCandidatesApi(() =>
    json({
      ...candidatePage([candidateFixture({ similarity: 0.66 })]),
      search_mode: "keyword",
    }),
  );
  renderAt("/documents?q=passport");

  expect(
    await screen.findAllByText(/Semantic matching is unavailable/),
  ).toHaveLength(1);
  expect(screen.queryByRole("progressbar", { name: /Similarity/ })).toBeNull();
  expect(
    screen.getByRole("progressbar", { name: /^Confidence/ }),
  ).toBeInTheDocument();
});
