import { screen, waitFor } from "@testing-library/react";
import { useLocation } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../../../test/renderWithProviders";
import DocumentFilters from "./DocumentFilters";

const fetchMock = vi.fn();

const domains = [
  { code: "housing", name: "Housing", description: "", icon: null },
  { code: "work", name: "Work", description: "", icon: null },
];
const situations = [
  { code: "moving", name: "Moving", description: "", icon: null },
];

function respond(failTaxonomy: boolean) {
  fetchMock.mockImplementation(async (url: string) => {
    const path = new URL(String(url)).pathname;
    if (failTaxonomy) return new Response("boom", { status: 500 });
    if (path.endsWith("/domains")) return new Response(JSON.stringify(domains));
    return new Response(JSON.stringify(situations));
  });
}

function LocationProbe() {
  return <output data-testid="search">{useLocation().search}</output>;
}

function renderFilters(url: string) {
  return renderWithProviders(
    <>
      <DocumentFilters />
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

it("DocumentFilters · taxonomy error shows compact error and no chips", async () => {
  respond(true);
  renderFilters("/documents");

  await waitFor(() =>
    expect(
      screen.getAllByRole("button", { name: /retry/i }).length,
    ).toBeGreaterThan(0),
  );
  expect(screen.queryByRole("button", { name: "Housing" })).toBeNull();
});
