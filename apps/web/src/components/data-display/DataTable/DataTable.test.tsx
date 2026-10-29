import { screen, within } from "@testing-library/react";
import { useLocation } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import DataTable from "./DataTable";
import type { DataTableColumn, DataTableProps } from "./types";

interface Row {
  id: string;
  name: string;
  count: number;
}
type SortKey = "name";
type FilterKey = "name";

const items: Row[] = [
  { id: "a", name: "Alpha", count: 3 },
  { id: "b", name: "Beta", count: 5 },
];

const columns: DataTableColumn<Row, SortKey, FilterKey>[] = [
  {
    key: "name",
    header: "Name",
    canSort: "name",
    filter: { key: "name", operators: ["contains"], label: "Filter name" },
    render: (row) => row.name,
  },
  { key: "count", header: "Count", render: (row) => row.count },
];

function Location() {
  return <output data-testid="location">{useLocation().pathname}</output>;
}

function renderTable(props: Partial<DataTableProps<Row, SortKey, FilterKey>>) {
  return renderWithProviders(
    <>
      <DataTable
        label="Services"
        columns={columns}
        rows={{ items, getKey: (row) => row.id }}
        {...props}
      />
      <Location />
    </>,
  );
}

describe("DataTable", () => {
  it("DataTable renders headers and cells from typed columns", () => {
    renderTable({});

    expect(screen.getByRole("table", { name: "Services" })).toBeInTheDocument();
    expect(screen.getAllByRole("columnheader")).toHaveLength(2);
    const row = screen.getByRole("row", { name: /Alpha/ });
    expect(within(row).getByRole("cell", { name: "Alpha" })).toBeVisible();
    expect(within(row).getByRole("cell", { name: "3" })).toBeVisible();
  });

  it("DataTable toggles a sortable column from ascending to descending", async () => {
    const onSortChange = vi.fn();
    const sort = { sortBy: "name", sortOrder: "asc" } as const;
    const { user } = renderTable({ query: { sort, onSortChange } });

    expect(screen.getByRole("columnheader", { name: /Name/ })).toHaveAttribute(
      "aria-sort",
      "ascending",
    );
    await user.click(screen.getByRole("button", { name: "Name" }));

    expect(onSortChange).toHaveBeenCalledExactlyOnceWith({
      sortBy: "name",
      sortOrder: "desc",
    });
  });

  it("DataTable omits controls for a display-only column", async () => {
    const onSortChange = vi.fn();
    const onFilterChange = vi.fn();
    const { user } = renderTable({ query: { onSortChange, onFilterChange } });

    const header = screen.getByRole("columnheader", { name: "Count" });
    expect(within(header).queryByRole("button")).not.toBeInTheDocument();
    expect(within(header).queryByRole("textbox")).not.toBeInTheDocument();
    expect(header).not.toHaveAttribute("aria-sort");
    await user.click(header);

    expect(onSortChange).not.toHaveBeenCalled();
    expect(onFilterChange).not.toHaveBeenCalled();
  });

  it("DataTable keeps a filter draft local until Apply emits it", async () => {
    const onFilterChange = vi.fn();
    const { user } = renderTable({ query: { onFilterChange } });

    await user.click(screen.getByRole("button", { name: "Filter name" }));
    await user.type(screen.getByRole("textbox", { name: "Filter name" }), "x");
    expect(onFilterChange).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Apply" }));

    expect(onFilterChange).toHaveBeenCalledExactlyOnceWith({
      key: "name",
      value: "x",
    });
  });

  it("DataTable discards an unapplied filter draft when the popover closes", async () => {
    const onFilterChange = vi.fn();
    const { user } = renderTable({
      query: { onFilterChange, filters: { name: "Al" } },
    });

    await user.click(screen.getByRole("button", { name: "Filter name" }));
    await user.type(screen.getByRole("textbox", { name: "Filter name" }), "x");
    await user.keyboard("{Escape}");
    await user.click(screen.getByRole("button", { name: "Filter name" }));

    expect(onFilterChange).not.toHaveBeenCalled();
    expect(screen.getByRole("textbox", { name: "Filter name" })).toHaveValue(
      "Al",
    );
  });

  it("DataTable offers a bounded filter as options with an any choice", async () => {
    const onFilterChange = vi.fn();
    const bounded: DataTableColumn<Row, SortKey, FilterKey>[] = [
      {
        key: "name",
        header: "Name",
        filter: {
          key: "name",
          operators: ["eq"],
          label: "Filter name",
          options: [
            { value: "Alpha", label: "Alpha team" },
            { value: "Beta", label: "Beta team" },
          ],
        },
        render: (row) => row.name,
      },
    ];
    const { user } = renderTable({
      columns: bounded,
      query: { onFilterChange },
    });

    await user.click(screen.getByRole("button", { name: "Filter name" }));
    const select = screen.getByRole("combobox", { name: "Filter name" });
    expect(
      within(select)
        .getAllByRole("option")
        .map((option) => option.textContent),
    ).toEqual(["Any", "Alpha team", "Beta team"]);
    await user.selectOptions(select, "Beta");
    await user.click(screen.getByRole("button", { name: "Apply" }));

    expect(onFilterChange).toHaveBeenCalledExactlyOnceWith({
      key: "name",
      value: "Beta",
    });
  });

  it("DataTable lists applied filters as removable chips with a clear-all", async () => {
    const onFilterChange = vi.fn();
    const onFiltersClear = vi.fn();
    const { user } = renderTable({
      query: { onFilterChange, onFiltersClear, filters: { name: "Al" } },
    });

    expect(screen.getByText("Filter name: Al")).toBeVisible();
    await user.click(
      screen.getByRole("button", { name: "Remove filter Filter name" }),
    );
    expect(onFilterChange).toHaveBeenCalledExactlyOnceWith({
      key: "name",
      value: "",
    });
    await user.click(screen.getByRole("button", { name: "Clear all filters" }));
    expect(onFiltersClear).toHaveBeenCalledOnce();
  });

  it("DataTable shows no filter summary without an applied filter", () => {
    renderTable({
      query: { onFilterChange: vi.fn(), onFiltersClear: vi.fn(), filters: {} },
    });

    expect(screen.queryByText(/Filter name:/)).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Clear all filters" }),
    ).not.toBeInTheDocument();
  });

  it("DataTable shows explicit error and empty states", async () => {
    const onRetry = vi.fn();
    const status = {
      isLoading: false,
      isRefreshing: false,
      isError: true,
      error: new Error("boom"),
      onRetry,
    };
    const { user, unmount } = renderTable({
      rows: { items: [], getKey: (row) => row.id },
      states: { status },
    });

    expect(screen.queryByText("Alpha")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalledOnce();
    unmount();

    renderTable({
      rows: { items: [], getKey: (row) => row.id },
      states: { status: { ...status, isError: false }, empty: "Nothing yet" },
    });
    expect(screen.getByText("Nothing yet")).toBeVisible();
    expect(
      screen.queryByRole("row", { name: /Alpha/ }),
    ).not.toBeInTheDocument();
  });

  it("DataTable keeps previous rows visible and busy while refreshing", () => {
    const status = {
      isLoading: false,
      isRefreshing: true,
      isError: false,
      error: null,
      onRetry: vi.fn(),
    };
    renderTable({ states: { status } });

    expect(screen.getByRole("table")).toHaveAttribute("aria-busy", "true");
    expect(screen.getByText("Alpha")).toBeVisible();
  });

  it("DataTable keeps previous rows and offers a retry when a refetch fails", async () => {
    const onRetry = vi.fn();
    const status = {
      isLoading: false,
      isRefreshing: false,
      isError: true,
      error: new Error("boom"),
      onRetry,
    };
    const { user } = renderTable({ states: { status } });

    expect(screen.getByText("Alpha")).toBeVisible();
    expect(screen.getByText("Beta")).toBeVisible();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Could not refresh the list",
    );
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("DataTable shows no refetch alert while the request succeeds", () => {
    const status = {
      isLoading: false,
      isRefreshing: false,
      isError: false,
      error: null,
      onRetry: vi.fn(),
    };
    renderTable({ states: { status } });

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("DataTable shows the loading slot instead of rows while loading", () => {
    const status = {
      isLoading: true,
      isRefreshing: false,
      isError: false,
      error: null,
      onRetry: vi.fn(),
    };
    renderTable({ states: { status, loading: "Loading rows" } });

    expect(screen.getByText("Loading rows")).toBeVisible();
    expect(screen.queryByText("Alpha")).not.toBeInTheDocument();
  });

  it("DataTable navigates from a row but not from a nested control", async () => {
    const withLink: DataTableColumn<Row, SortKey, FilterKey>[] = [
      ...columns,
      {
        key: "action",
        header: "Action",
        render: () => <button type="button">Retry</button>,
      },
    ];
    const rows = {
      items,
      getKey: (r: Row) => r.id,
      getHref: (r: Row) => `/r/${r.id}`,
    };
    const { user } = renderTable({ columns: withLink, rows });

    await user.click(screen.getAllByRole("button", { name: "Retry" })[0]);
    expect(screen.getByTestId("location")).toHaveTextContent("/");

    await user.click(screen.getByText("Beta"));
    expect(screen.getByTestId("location")).toHaveTextContent("/r/b");
  });

  it("DataTable renders no pagination for a single page", () => {
    renderTable({
      page: { offset: 0, limit: 20, total: 2, onOffsetChange: vi.fn() },
    });

    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
  });
});
