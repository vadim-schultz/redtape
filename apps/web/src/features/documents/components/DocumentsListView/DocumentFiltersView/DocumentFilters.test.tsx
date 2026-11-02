import { screen, waitFor } from "@testing-library/react";
import { useLocation } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../../../test/renderWithProviders";
import { useFilterTaxonomy } from "../../../hooks/useFilterTaxonomy";
import { useDocumentFilters } from "../../../hooks/useDocumentFilters";
import DocumentFilters from "./DocumentFilters";

const fetchMock = vi.fn();

const domains = [
  { code: "housing", name: "Housing", description: "", icon: null },
  { code: "work", name: "Work", description: "", icon: null },
];
const groups = [{ code: "home", name: "Home", description: "", icon: null }];
const situations = [
  {
    code: "moving",
    name: "Moving",
    description: "",
    icon: null,
    group_code: "home",
  },
];

function respond(failTaxonomy: boolean) {
  fetchMock.mockImplementation(async (url: string) => {
    const path = new URL(String(url)).pathname;
    if (failTaxonomy) return new Response("boom", { status: 500 });
    if (path.endsWith("/domains")) return new Response(JSON.stringify(domains));
    if (path.endsWith("/life-situation-groups"))
      return new Response(JSON.stringify(groups));
    return new Response(JSON.stringify(situations));
  });
}

function LocationProbe() {
  return <output data-testid="search">{useLocation().search}</output>;
}

function Container() {
  return (
    <DocumentFilters
      taxonomy={useFilterTaxonomy()}
      filters={useDocumentFilters()}
    />
  );
}

function renderFilters(url: string) {
  return renderWithProviders(
    <>
      <Container />
      <LocationProbe />
    </>,
    { initialEntries: [url] },
  );
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  respond(false);
});
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

it("DocumentFilters · clear removes all filters", async () => {
  const { user } = renderFilters("/documents?domain=housing&situation=moving");
  await screen.findByRole("button", { name: "Housing" });

  await user.click(screen.getByRole("button", { name: /clear/i }));

  expect(screen.getByTestId("search")).toHaveTextContent("");
  expect(screen.getByRole("button", { name: "Housing" })).toHaveAttribute(
    "aria-pressed",
    "false",
  );
});

it("DocumentFilters · clicking a chip writes the code to the URL", async () => {
  const { user } = renderFilters("/documents");

  await user.click(await screen.findByRole("button", { name: "Work" }));

  expect(screen.getByTestId("search")).toHaveTextContent("?domain=work");
});

it("DocumentFilters · unknown code in the URL is ignored with no crash", async () => {
  renderFilters("/documents?domain=nope");

  const chip = await screen.findByRole("button", { name: "Housing" });

  expect(chip).toHaveAttribute("aria-pressed", "false");
  expect(screen.getByRole("button", { name: "Work" })).toHaveAttribute(
    "aria-pressed",
    "false",
  );
});

it("DocumentFilters · a situation selected via the URL auto-expands its group", async () => {
  renderFilters("/documents?situation=moving");

  await screen.findByRole("button", { name: "Home" });

  expect(screen.getByRole("button", { name: "Moving" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});

it("DocumentFilters · taxonomy error shows compact error and no chips", async () => {
  respond(true);
  renderFilters("/documents");

  await waitFor(() =>
    expect(
      screen.getAllByRole("button", { name: /try again/i }).length,
    ).toBeGreaterThan(0),
  );
  expect(screen.queryByRole("button", { name: "Housing" })).toBeNull();
});

const noopFilters = {
  domains: [],
  situations: [],
  leaves: [],
  toggleDomain: vi.fn(),
  toggleSituation: vi.fn(),
  toggleLeaf: vi.fn(),
  clear: vi.fn(),
};

function renderPresentational(taxonomy: {
  isError: boolean;
  onRetry: () => void;
}) {
  const props = { domains, situations, groups, ...taxonomy };
  return renderWithProviders(
    <DocumentFilters taxonomy={props} filters={noopFilters} />,
  );
}

it("DocumentFilters · renders the terms it is given without calling an API", () => {
  renderPresentational({ isError: false, onRetry: vi.fn() });

  expect(screen.getByRole("button", { name: "Housing" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Home" })).toBeInTheDocument();
  expect(fetchMock).not.toHaveBeenCalledWith(
    expect.stringContaining("/domains"),
    expect.anything(),
  );
});

it("DocumentFilters · expanding a situation group reveals its situation chip", async () => {
  const { user } = renderPresentational({ isError: false, onRetry: vi.fn() });

  await user.click(screen.getByRole("button", { name: "Home" }));

  expect(screen.getByRole("button", { name: "Moving" })).toBeInTheDocument();
});

it("DocumentFilters · renders a leaf facet chip when given available leaf codes", () => {
  const props = {
    domains,
    situations,
    groups,
    isError: false,
    onRetry: vi.fn(),
  };
  renderWithProviders(
    <DocumentFilters
      taxonomy={props}
      filters={noopFilters}
      availableLeafCodes={["1050200"]}
    />,
  );

  expect(screen.getByRole("button", { name: "1050200" })).toBeInTheDocument();
});

it("DocumentFilters · error flag shows retry, which calls onRetry only", async () => {
  const onRetry = vi.fn();
  const { user } = renderPresentational({ isError: true, onRetry });

  await user.click(screen.getByRole("button", { name: /try again/i }));

  expect(onRetry).toHaveBeenCalledTimes(1);
  expect(screen.queryByRole("button", { name: "Housing" })).toBeNull();
  const taxonomyCalls = fetchMock.mock.calls.filter(([url]) =>
    /domains|life-situations|situations/.test(String(url)),
  );
  expect(taxonomyCalls).toHaveLength(0);
});
