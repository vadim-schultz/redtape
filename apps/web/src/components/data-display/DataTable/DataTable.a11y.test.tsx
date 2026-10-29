import { screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { emotionRules } from "../../../test/emotionRules";
import { renderWithProviders } from "../../../test/renderWithProviders";
import { expectAccessibleTables } from "../../../test/tableAccessibility";
import DataTable from "./DataTable";
import type { DataTableColumn, DataTableProps } from "./types";

interface Row {
  id: string;
  name: string;
  count: number;
  note: string;
}
type SortKey = "name";
type FilterKey = "name";

const note = `https://example.gov/${"very-long-segment/".repeat(12)}end`;
const items: Row[] = [
  { id: "a", name: "Alpha", count: 3, note },
  { id: "b", name: "Beta", count: 5, note: "short" },
];

const columns: DataTableColumn<Row, SortKey, FilterKey>[] = [
  {
    key: "name",
    header: "Name",
    canSort: "name",
    filter: { key: "name", operators: ["contains"], label: "Filter name" },
    render: (row) => row.name,
  },
  { key: "count", header: "Count", align: "end", render: (row) => row.count },
  { key: "note", header: "Note", render: (row) => row.note },
];

function renderTable(props: Partial<DataTableProps<Row, SortKey, FilterKey>>) {
  return renderWithProviders(
    <DataTable
      label="Services"
      columns={columns}
      rows={{ items, getKey: (row) => row.id }}
      query={{ onSortChange: vi.fn(), onFilterChange: vi.fn() }}
      {...props}
    />,
  );
}

describe("DataTable accessibility", () => {
  it("DataTable exposes headers, row cells, and named sort/filter controls", async () => {
    const { user, container } = renderTable({});

    expect(screen.getAllByRole("columnheader")).toHaveLength(3);
    expect(screen.getByRole("columnheader", { name: /Name/ })).toHaveAttribute(
      "aria-sort",
      "none",
    );
    expect(screen.getByRole("button", { name: "Name" })).toBeVisible();
    const trigger = screen.getByRole("button", { name: "Filter name" });
    expect(trigger).toHaveAttribute("aria-haspopup", "dialog");
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expectAccessibleTables(container);

    await user.click(trigger);

    expect(trigger).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("dialog", { name: "Filter name" })).toBeVisible();
  });

  it("DataTable reaches sort and filter controls by keyboard alone", async () => {
    const onSortChange = vi.fn();
    const { user } = renderTable({
      query: { onSortChange, onFilterChange: vi.fn() },
    });

    await user.tab();
    await user.tab();
    expect(screen.getByRole("button", { name: "Name" })).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(onSortChange).toHaveBeenCalledOnce();

    await user.tab();
    expect(screen.getByRole("button", { name: "Filter name" })).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("textbox", { name: "Filter name" })).toBeVisible();
  });

  it("long table values remain inspectable at narrow width", () => {
    renderTable({});

    const scroller = screen.getByRole("group", {
      name: "Services, scrollable",
    });
    expect(scroller).toHaveAttribute("tabindex", "0");
    expect(emotionRules(scroller)).toContain("overflow: auto");
    expect(within(scroller).getByRole("table")).toBe(
      screen.getByRole("table", { name: "Services" }),
    );
    expect(within(scroller).getByText(note)).toBeInTheDocument();
  });

  it("DataTable aligns a column's header and cells together", () => {
    renderTable({});

    const header = screen.getByRole("columnheader", { name: "Count" });
    const cell = screen.getByRole("cell", { name: "3" });
    const unaligned = screen.getByRole("columnheader", { name: /Name/ });

    expect(emotionRules(header)).toContain("text-align: end");
    expect(emotionRules(cell)).toContain("text-align: end");
    expect(emotionRules(unaligned)).not.toContain("text-align: end");
    expect(
      emotionRules(screen.getByRole("cell", { name: "Alpha" })),
    ).not.toContain("text-align: end");
  });

  it("DataTable raises the filter popover on the overlay surface", async () => {
    const { user } = renderTable({});

    await user.click(screen.getByRole("button", { name: "Filter name" }));
    const rules = emotionRules(screen.getByRole("dialog"));

    expect(rules).toContain("var(--chakra-colors-surface-overlay)");
    expect(rules).toContain("var(--chakra-shadows-dropdown)");
  });
});
