import { describe, expect, it } from "vitest";

import { activeFilters } from "./filters";
import type { DataTableColumn } from "./types";

type Row = { id: string };

const columns: DataTableColumn<Row, never, "status" | "kind">[] = [
  {
    key: "status",
    header: "Status",
    filter: {
      key: "status",
      operators: ["eq"],
      label: "Task status",
      options: [{ value: "failed", label: "Failed tasks" }],
    },
    render: () => null,
  },
  {
    key: "kind",
    header: "Kind",
    filter: { key: "kind", operators: ["contains"], label: "Task kind" },
    render: () => null,
  },
  { key: "id", header: "Id", render: () => null },
];

describe("activeFilters", () => {
  it("lists applied filters in column order with the option label as display", () => {
    expect(activeFilters(columns, { kind: "fetch", status: "failed" })).toEqual(
      [
        { key: "status", label: "Task status", display: "Failed tasks" },
        { key: "kind", label: "Task kind", display: "fetch" },
      ],
    );
  });

  it("skips empty, undefined and undeclared filter values", () => {
    expect(activeFilters(columns, { status: undefined, kind: "" })).toEqual([]);
    expect(activeFilters(columns, undefined)).toEqual([]);
  });

  it("shows a numeric value as text", () => {
    expect(activeFilters(columns, { kind: 3 })).toEqual([
      { key: "kind", label: "Task kind", display: "3" },
    ]);
  });
});
