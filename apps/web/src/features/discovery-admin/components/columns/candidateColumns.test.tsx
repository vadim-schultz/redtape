import { screen, within } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import {
  DataTable,
  type DataTableProps,
} from "../../../../components/data-display/DataTable";
import { useLocale } from "../../../../contexts/LocaleContext";
import { emotionRules } from "../../../../test/emotionRules";
import { renderWithProviders } from "../../../../test/renderWithProviders";
import type {
  CandidateFilterKey,
  CandidateSortKey,
  DiscoveryCandidate,
} from "../../types";
import { candidateColumns } from "./candidateColumns";

beforeEach(() => window.localStorage.setItem("locale", "en"));

const row: DiscoveryCandidate = {
  id: "cand-1",
  jurisdiction_id: "jur-1",
  key: "personalausweis",
  title_i18n: { de: "Personalausweis" },
  official_url: null,
  status: "staged",
  suggestion_id: null,
  mention_count: 7,
  roles: ["form"],
  jurisdiction_name_i18n: { en: "Germany" },
  created_at: "2026-01-01T12:00:00Z",
  updated_at: "2026-01-01T12:00:00Z",
  completeness: 4,
  complete: false,
  flags: {
    has_domain: true,
    has_situation: true,
    has_edges: true,
    has_snapshot: true,
    has_screenshot: false,
  },
};

type Query = NonNullable<
  DataTableProps<
    DiscoveryCandidate,
    CandidateSortKey,
    CandidateFilterKey
  >["query"]
>;

function Table({
  query,
  item = row,
}: {
  query: Query;
  item?: DiscoveryCandidate;
}) {
  return (
    <DataTable
      label="Documents"
      columns={candidateColumns(useLocale())}
      rows={{ items: [item], getKey: (item) => item.id }}
      query={query}
    />
  );
}

it("every sortable candidate column sets the sort key of the admin contract on header click", async () => {
  const onSortChange = vi.fn();
  const { user } = renderWithProviders(<Table query={{ onSortChange }} />);

  for (const name of [
    "Title",
    "Jurisdiction",
    "Roles",
    "Mentions",
    "Status",
    "Readiness",
    "First seen",
  ]) {
    await user.click(screen.getByRole("button", { name }));
  }

  expect(onSortChange.mock.calls.map(([sort]) => sort.sortBy)).toEqual([
    "title",
    "jurisdiction",
    "roles",
    "mentions",
    "status",
    "completeness",
    "created_at",
  ]);
});

it("candidate columns declare a filter on roles, mentions, status and readiness only", () => {
  renderWithProviders(<Table query={{ onFilterChange: vi.fn() }} />);

  for (const label of [
    "Role",
    "Minimum mentions",
    "Document status",
    "Completeness",
  ]) {
    expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
  }
  for (const name of ["Title", "Jurisdiction", "First seen"]) {
    const header = screen.getByRole("columnheader", { name });
    expect(within(header).getAllByRole("button")).toHaveLength(1);
  }
});

it("a column filter applies the contract key and value", async () => {
  const onFilterChange = vi.fn();
  const { user } = renderWithProviders(<Table query={{ onFilterChange }} />);

  await user.click(screen.getByRole("button", { name: "Document status" }));
  await user.selectOptions(screen.getByLabelText("Document status"), "staged");
  await user.click(screen.getByRole("button", { name: "Apply" }));

  expect(onFilterChange).toHaveBeenCalledExactlyOnceWith({
    key: "status",
    value: "staged",
  });
});

it("readiness column shows five flags per row and names the missing one", () => {
  renderWithProviders(<Table query={{}} />);

  const cell = screen.getByRole("cell", { name: /Screenshot: missing/ });
  expect(within(cell).getAllByRole("listitem")).toHaveLength(5);
  expect(
    within(cell).getByRole("listitem", { name: "Screenshot: missing" }),
  ).toBeInTheDocument();
  expect(
    within(cell).getByRole("listitem", { name: "Domain: present" }),
  ).toBeInTheDocument();
});

it("long title is clipped to the column width and linked by its full text", () => {
  const long = "T".repeat(200);
  renderWithProviders(
    <Table query={{}} item={{ ...row, title_i18n: { de: long } }} />,
  );

  const link = screen.getByRole("link", { name: long });
  expect(emotionRules(link)).toContain("max-width: 28rem");
  expect(emotionRules(link.closest("td") as HTMLElement)).toContain(
    "max-width: 28rem",
  );
});

it("no row text is lost when the title is clipped", () => {
  const long = "T".repeat(200);
  renderWithProviders(
    <Table query={{}} item={{ ...row, title_i18n: { de: long } }} />,
  );

  const cells = screen.getAllByRole("cell").map((cell) => cell.textContent);
  expect(cells[0]).toBe(long);
  expect(cells).toContain("Germany");
  expect(cells).toContain("7");
});

it("candidate columns align the mention count to the end", () => {
  renderWithProviders(<Table query={{}} />);

  const header = screen.getByRole("columnheader", { name: /Mentions/ });
  const title = screen.getByRole("columnheader", { name: /Title/ });

  expect(emotionRules(header)).toContain("text-align: end");
  expect(emotionRules(title)).not.toContain("text-align: end");
});
