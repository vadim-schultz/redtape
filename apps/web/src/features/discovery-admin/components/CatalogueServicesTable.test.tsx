import { screen, within } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import type { CatalogueServiceSummary } from "../types";
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

it("catalogue, mentions, and nested admin lists use the shared table contract (catalogue)", () => {
  renderWithProviders(<CatalogueServicesTable items={[service]} />);

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
  renderWithProviders(<CatalogueServicesTable items={[]} />);

  const table = screen.getByRole("table", { name: "Catalogue services" });
  expect(within(table).getByText("No catalogue services yet.")).toBeVisible();
  expect(within(table).queryByRole("link")).not.toBeInTheDocument();
});
