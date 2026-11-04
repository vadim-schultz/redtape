import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { expect, it } from "vitest";

import type { CategoryNode } from "../../taxonomy/types";
import { useDocumentFilters } from "./useDocumentFilters";

const tree: CategoryNode[] = [
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

function renderFilters(url: string) {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <MemoryRouter initialEntries={[url]}>{children}</MemoryRouter>
  );
  return renderHook(
    () => ({
      filters: useDocumentFilters(tree),
      location: useLocation(),
    }),
    { wrapper },
  );
}

it("category filter · selecting a root serializes one category code", () => {
  const { result } = renderFilters("/documents");

  act(() => result.current.filters.toggleCategory("home-and-housing"));

  expect(result.current.location.search).toBe("?category=home-and-housing");
});

it("category filter · selecting a subcategory serializes its exact code", () => {
  const { result } = renderFilters(
    "/documents?category=home-and-housing&domain=legacy",
  );

  act(() =>
    result.current.filters.toggleCategory("moving-house", "home-and-housing"),
  );

  const params = new URLSearchParams(result.current.location.search);
  expect(params.getAll("category")).toEqual(["moving-house"]);
  expect(params.get("domain")).toBe("legacy");
  expect(result.current.filters.categories).toEqual(["moving-house"]);
});

it("legacy URL · old axis parameters remain available to the compatibility API", () => {
  const { result } = renderFilters(
    "/documents?domain=identity&group=home&situation=moving",
  );

  expect(result.current.filters.legacy).toEqual({
    domain: ["identity"],
    group: ["home"],
    situation: ["moving"],
  });
});

it("category filter · unknown URL category does not produce a valid taxonomy selection", () => {
  const { result } = renderFilters("/documents?category=ghost");

  expect(result.current.filters.categories).toEqual([]);
});
