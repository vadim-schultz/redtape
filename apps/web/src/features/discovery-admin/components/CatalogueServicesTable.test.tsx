import { screen, within } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import type { QueryStatus } from "../../../components/feedback/queryStatus";
import { fakeListController } from "../../../test/fakeListController";
import { renderWithProviders } from "../../../test/renderWithProviders";
import type {
  CatalogueFilterKey,
  CatalogueServiceSummary,
  CatalogueSortKey,
} from "../types";
import CatalogueServicesTable from "./CatalogueServicesTable";

beforeEach(() => window.localStorage.setItem("locale", "en"));

const service: CatalogueServiceSummary = {
  id: "cat-1",
  source: "pvog",
  external_id: "service-1",
  jurisdiction_id: "jur-1",
  title_i18n: { en: "Example" },
  pipeline_stage: "T3",
  portal_url: "https://example.gov/service",
  created_at: "2026-01-01T12:00:00Z",
  updated_at: "2026-01-01T12:00:00Z",
};

const READY: QueryStatus = {
  isLoading: false,
  isRefreshing: false,
  isError: false,
  error: null,
  onRetry: vi.fn(),
};

const fakeList = () =>
  fakeListController<CatalogueSortKey, CatalogueFilterKey>();

function pageOf(items: CatalogueServiceSummary[], total = items.length) {
  return {
    items,
    total,
    offset: 0,
    limit: 20,
    summary: { total, by_source: {}, by_pipeline_stage: {} },
  };
}

it("catalogue, mentions, and nested admin lists use the shared table contract (catalogue)", () => {
  renderWithProviders(
    <CatalogueServicesTable
      page={pageOf([service])}
      status={READY}
      list={fakeList()}
    />,
  );

  const table = screen.getByRole("table", { name: "Catalogue services" });
  expect(
    within(table)
      .getAllByRole("columnheader")
      .map((header) => header.textContent),
  ).toEqual(["External ID", "Source", "Stage"]);
  const row = within(screen.getByRole("row", { name: /service-1/ }));
  expect(row.getByRole("link", { name: "service-1" })).toHaveAttribute(
    "href",
    "/admin/discovery/pipeline/cat-1",
  );
  expect(row.getByText("pvog")).toBeInTheDocument();
  expect(row.getByText("T3")).toBeInTheDocument();
});

it("catalogue table renders the empty message inside the table and no rows", () => {
  renderWithProviders(
    <CatalogueServicesTable
      page={pageOf([])}
      status={READY}
      list={fakeList()}
    />,
  );

  const table = screen.getByRole("table", { name: "Catalogue services" });
  expect(within(table).getByText("No catalogue services")).toBeVisible();
  expect(within(table).queryByRole("link")).not.toBeInTheDocument();
});

it("catalogue table shows the total and pages through the list controller", async () => {
  const list = fakeList();
  const { user } = renderWithProviders(
    <CatalogueServicesTable
      page={pageOf([service], 120)}
      status={READY}
      list={list}
    />,
  );

  expect(screen.getByText("120 catalogue services")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Next page" }));
  expect(list.setOffset).toHaveBeenCalledExactlyOnceWith(20);
});

it("catalogue table sorts and filters only by the allowlisted keys", async () => {
  const list = fakeList();
  const { user } = renderWithProviders(
    <CatalogueServicesTable
      page={pageOf([service])}
      status={READY}
      list={list}
    />,
  );

  await user.click(screen.getByRole("button", { name: "Stage" }));
  expect(list.setSort).toHaveBeenCalledExactlyOnceWith({
    sortBy: "stage",
    sortOrder: "asc",
  });
  await user.click(screen.getByRole("button", { name: "Catalogue source" }));
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Catalogue source" }),
    "pvog",
  );
  await user.click(screen.getByRole("button", { name: "Apply" }));
  expect(list.setFilter).toHaveBeenCalledExactlyOnceWith("source", "pvog");
});

it("header toolbar is absent from the catalogue table", () => {
  renderWithProviders(
    <CatalogueServicesTable
      page={pageOf([service])}
      status={READY}
      list={fakeList()}
    />,
  );

  const card = screen.getByRole("table").closest("[data-section-card]");
  expect(card).not.toBeNull();
  expect(card?.querySelector("[data-section-header]")).toBeNull();
});
