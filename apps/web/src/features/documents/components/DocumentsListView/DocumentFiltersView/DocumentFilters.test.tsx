import { screen, waitFor } from "@testing-library/react";
import { useLocation } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../../../test/renderWithProviders";
import { useFilterTaxonomy } from "../../../hooks/useFilterTaxonomy";
import { useDocumentFilters } from "../../../hooks/useDocumentFilters";
import DocumentFilters from "./DocumentFilters";

const fetchMock = vi.fn();
const tree = [
  {
    code: "home-and-housing",
    name: "Home & housing",
    description: "",
    icon: "home",
    parent_code: null,
    children: [
      {
        code: "moving-house",
        name: "Moving house",
        description: "",
        icon: null,
        parent_code: "home-and-housing",
        children: [],
      },
    ],
  },
];

function Container() {
  const taxonomy = useFilterTaxonomy();
  return (
    <DocumentFilters
      taxonomy={taxonomy}
      filters={useDocumentFilters(taxonomy.categories)}
    />
  );
}

function LocationProbe() {
  return <output data-testid="search">{useLocation().search}</output>;
}

function respond(status = 200) {
  fetchMock.mockResolvedValue(
    new Response(status === 200 ? JSON.stringify(tree) : "boom", { status }),
  );
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  respond();
});

afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

it("DocumentFilters · selecting a root writes its canonical category code", async () => {
  const { user } = renderWithProviders(
    <>
      <Container />
      <LocationProbe />
    </>,
    {
      initialEntries: ["/documents"],
    },
  );

  await user.click(
    await screen.findByRole("button", { name: "Home & housing" }),
  );

  expect(screen.getByTestId("search")).toHaveTextContent(
    "?category=home-and-housing",
  );
  expect(
    screen.getByRole("button", { name: "Home & housing" }),
  ).toHaveAttribute("aria-pressed", "true");
});

it("category tree · failed query renders the existing query error and no stale chips", async () => {
  respond(500);
  renderWithProviders(<Container />, { initialEntries: ["/documents"] });

  await waitFor(() =>
    expect(
      screen.getAllByRole("button", { name: /try again/i }),
    ).not.toHaveLength(0),
  );
  expect(screen.queryByRole("button", { name: "Home & housing" })).toBeNull();
});
