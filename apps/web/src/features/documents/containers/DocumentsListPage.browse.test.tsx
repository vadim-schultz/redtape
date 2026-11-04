import { screen, waitFor, within } from "@testing-library/react";
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
  return <p data-testid="search">{useLocation().search}</p>;
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

const urlParams = () =>
  new URLSearchParams(screen.getByTestId("search").textContent ?? "");
const lastCall = (fetchMock: ReturnType<typeof stubCandidatesApi>) =>
  listCalls(fetchMock).at(-1)!.searchParams;
const twenty = Array.from({ length: 20 }, (_, i) =>
  candidateFixture({ id: `c${i}`, title: `Doc ${i}` }),
);
const passport = candidateFixture({ title: "Passport" });

function stubPage(items = [passport], total = items.length) {
  return stubCandidatesApi(() => json(candidatePage(items, total)));
}

it("DocumentsListPage · submitting a search writes q to the URL and refetches", async () => {
  const fetchMock = stubPage();
  const { user } = renderAt("/documents?offset=40");
  await screen.findByRole("link", { name: /Passport/ });

  await user.type(
    screen.getByRole("textbox", { name: "Search document titles" }),
    "ausweis{Enter}",
  );

  expect(urlParams().get("q")).toBe("ausweis");
  expect(urlParams().has("offset")).toBe(false);
  await waitFor(() => expect(lastCall(fetchMock).get("q")).toBe("ausweis"));
});

it("DocumentsListPage · a blank search removes q instead of sending it", async () => {
  const fetchMock = stubPage();
  const { user } = renderAt("/documents?q=ausweis");
  await screen.findByRole("link", { name: /Passport/ });

  const box = screen.getByRole("textbox", { name: "Search document titles" });
  await user.clear(box);
  await user.type(box, "   {Enter}");

  expect(urlParams().has("q")).toBe(false);
  await waitFor(() => expect(lastCall(fetchMock).has("q")).toBe(false));
});

it("DocumentsListPage · the sort select shows confidence descending by default", async () => {
  const fetchMock = stubPage();
  renderAt("/documents");
  await screen.findByRole("link", { name: /Passport/ });

  expect(screen.getByRole("combobox", { name: "Sort by" })).toHaveValue(
    "confidence",
  );
  expect(screen.getByRole("button", { name: "Descending" })).toBeVisible();
  expect(lastCall(fetchMock).has("sort_by")).toBe(false);
});

it("DocumentsListPage · changing the sort writes sort_by and sort_order", async () => {
  const fetchMock = stubPage();
  const { user } = renderAt("/documents?offset=20");
  await screen.findByRole("link", { name: /Passport/ });

  await user.selectOptions(
    screen.getByRole("combobox", { name: "Sort by" }),
    "Title",
  );

  expect(urlParams().get("sort_by")).toBe("title");
  expect(urlParams().get("sort_order")).toBe("asc");
  expect(urlParams().has("offset")).toBe(false);
  await waitFor(() => expect(lastCall(fetchMock).get("sort_by")).toBe("title"));

  await user.click(screen.getByRole("button", { name: "Ascending" }));

  expect(urlParams().get("sort_order")).toBe("desc");
  await waitFor(() =>
    expect(lastCall(fetchMock).get("sort_order")).toBe("desc"),
  );
});

it("DocumentsListPage · going back to confidence descending clears the sort params", async () => {
  stubPage();
  const { user } = renderAt("/documents?sort_by=title&sort_order=asc");
  await screen.findByRole("link", { name: /Passport/ });

  await user.selectOptions(
    screen.getByRole("combobox", { name: "Sort by" }),
    "Confidence",
  );

  expect(urlParams().has("sort_by")).toBe(false);
  expect(urlParams().has("sort_order")).toBe(false);
});

it("DocumentsListPage · an unknown sort key and a bad offset in the URL fall back to defaults", async () => {
  const fetchMock = stubPage();
  renderAt("/documents?sort_by=completeness&offset=-5");
  await screen.findByRole("link", { name: /Passport/ });

  expect(screen.getByRole("combobox", { name: "Sort by" })).toHaveValue(
    "confidence",
  );
  const params = lastCall(fetchMock);
  expect(params.has("sort_by")).toBe(false);
  expect(params.get("offset")).toBe("0");
});

it("DocumentsListPage · a page of 20 of 57 shows the pager and moves the offset", async () => {
  const fetchMock = stubPage(twenty, 57);
  const { user } = renderAt("/documents");
  const pager = await screen.findByRole("navigation", { name: "Pagination" });

  expect(pager).toHaveTextContent("1–20 of 57");
  await user.click(within(pager).getByRole("button", { name: "Page 2" }));

  await waitFor(() => expect(urlParams().get("offset")).toBe("20"));
  await waitFor(() => expect(lastCall(fetchMock).get("offset")).toBe("20"));
});

it("DocumentsListPage · a single page shows no pager", async () => {
  stubPage([passport], 1);
  renderAt("/documents");
  await screen.findByRole("link", { name: /Passport/ });

  expect(screen.queryByRole("navigation", { name: "Pagination" })).toBeNull();
});

it("DocumentsListPage · an empty filtered result offers to clear the chips and the search", async () => {
  stubCandidatesApi(() => json(candidatePage([])));
  const { user } = renderAt(
    "/documents?category=identity-and-documents&q=zzz&sort_by=title",
  );

  expect(await screen.findByText("No documents found")).toBeInTheDocument();
  expect(
    screen.getByText(/filters or search hide every document/i),
  ).toBeInTheDocument();
  await user.click(
    screen.getByRole("button", { name: "Clear filters and search" }),
  );

  expect([...urlParams().keys()]).toEqual(["sort_by"]);
});

it("DocumentsListPage · an empty unfiltered result has no clear action", async () => {
  stubCandidatesApi(() => json(candidatePage([])));
  renderAt("/documents");

  expect(await screen.findByText("No documents found")).toBeInTheDocument();
  expect(screen.getByText("No documents have been found yet.")).toBeVisible();
  expect(
    screen.queryByRole("button", { name: "Clear filters and search" }),
  ).toBeNull();
});
