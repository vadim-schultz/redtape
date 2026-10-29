import { screen, within } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import type { QueryStatus } from "../../../components/feedback/queryStatus";
import { edge } from "../../../test/discoveryAdminFixtures";
import { renderWithProviders } from "../../../test/renderWithProviders";
import DocumentEdgesPanel from "./DocumentEdgesPanel";

beforeEach(() => window.localStorage.setItem("locale", "en"));

const ready: QueryStatus = {
  isLoading: false,
  isRefreshing: false,
  isError: false,
  error: null,
  onRetry: vi.fn(),
};

const requires = edge({
  id: "e-1",
  parent_candidate_id: "doc-1",
  required_candidate_id: "req-1",
  required_title_i18n: { de: "Geburtsurkunde" },
  condition: "bei Zuzug aus dem Ausland",
  is_optional: true,
});
const derived = edge({
  id: "e-2",
  parent_candidate_id: "doc-1",
  required_candidate_id: "req-2",
  required_title_i18n: { de: "Meldebescheinigung" },
  basis: "derived_single_issued",
  catalogue_service_id: "cat-2",
  procedure_title_i18n: { en: "Register a move" },
});
const requiredBy = edge({
  id: "e-3",
  parent_candidate_id: "par-1",
  parent_title_i18n: { de: "Führerschein" },
  required_candidate_id: "doc-1",
});

function renderPanel(items: ReturnType<typeof edge>[], status = ready) {
  renderWithProviders(
    <DocumentEdgesPanel candidateId="doc-1" status={status} edges={items} />,
  );
}

it("catalogue, mentions, and nested admin lists use the shared table contract (edges)", () => {
  renderPanel([requires, derived, requiredBy]);

  const requiresTable = within(screen.getByRole("table", { name: "Requires" }));
  expect(
    requiresTable.getAllByRole("columnheader").map((cell) => cell.textContent),
  ).toEqual(["Document", "Condition", "Basis", "Procedure"]);
  const first = within(
    requiresTable.getByRole("link", { name: "Geburtsurkunde" }).closest("tr")!,
  );
  expect(
    requiresTable.getByRole("link", { name: "Geburtsurkunde" }),
  ).toHaveAttribute("href", "/admin/discovery/documents/req-1");
  expect(first.getByText("bei Zuzug aus dem Ausland")).toBeInTheDocument();
  expect(first.getByText("Optional")).toBeInTheDocument();
  expect(first.getByText("Explicit")).toBeInTheDocument();
  expect(
    first.getByRole("link", { name: "Apply for an ID card" }),
  ).toHaveAttribute("href", "/admin/discovery/pipeline/cat-1");
  expect(requiresTable.getByText("Derived")).toBeInTheDocument();
  expect(
    requiresTable.getByRole("link", { name: "Register a move" }),
  ).toHaveAttribute("href", "/admin/discovery/pipeline/cat-2");

  const requiredByTable = within(
    screen.getByRole("table", { name: "Required by" }),
  );
  expect(
    requiredByTable.getByRole("link", { name: "Führerschein" }),
  ).toHaveAttribute("href", "/admin/discovery/documents/par-1");
  expect(
    requiredByTable.queryByText("Geburtsurkunde"),
  ).not.toBeInTheDocument();
});

it("edges panel shows an empty state and the load error with a retry", () => {
  renderPanel([]);

  expect(screen.getByText("No dependencies staged yet.")).toBeInTheDocument();
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
});

it("edges panel shows the query error instead of the empty state", () => {
  renderPanel([], { ...ready, isError: true });

  expect(
    screen.queryByText("No dependencies staged yet."),
  ).not.toBeInTheDocument();
  expect(screen.getByRole("button")).toBeInTheDocument();
});
