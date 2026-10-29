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
};

type Query = NonNullable<
  DataTableProps<
    DiscoveryCandidate,
    CandidateSortKey,
    CandidateFilterKey
  >["query"]
>;

function Table({ query }: { query: Query }) {
  return (
    <DataTable
      label="Documents"
      columns={candidateColumns(useLocale())}
      rows={{ items: [row], getKey: (item) => item.id }}
      query={query}
    />
  );
}

it("candidate columns sort only by the keys the candidate contract declares", async () => {
  const onSortChange = vi.fn();
  const { user } = renderWithProviders(<Table query={{ onSortChange }} />);

  await user.click(screen.getByRole("button", { name: "Mentions" }));
  await user.click(screen.getByRole("button", { name: "Title" }));
  await user.click(screen.getByRole("button", { name: "First seen" }));

  expect(onSortChange.mock.calls.map(([sort]) => sort.sortBy)).toEqual([
    "mentions",
    "title",
    "created_at",
  ]);
});

it("candidate columns give display-only columns no sort or filter control", async () => {
  const onSortChange = vi.fn();
  const onFilterChange = vi.fn();
  const { user } = renderWithProviders(
    <Table query={{ onSortChange, onFilterChange }} />,
  );

  for (const name of ["Jurisdiction", "Roles", "Status"]) {
    const header = screen.getByRole("columnheader", { name });
    expect(within(header).queryByRole("button")).not.toBeInTheDocument();
    expect(header).not.toHaveAttribute("aria-sort");
    await user.click(header);
  }

  expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  expect(onSortChange).not.toHaveBeenCalled();
  expect(onFilterChange).not.toHaveBeenCalled();
});

it("candidate columns align the mention count to the end", () => {
  renderWithProviders(<Table query={{}} />);

  const header = screen.getByRole("columnheader", { name: /Mentions/ });
  const title = screen.getByRole("columnheader", { name: /Title/ });

  expect(emotionRules(header)).toContain("text-align: end");
  expect(emotionRules(title)).not.toContain("text-align: end");
});
