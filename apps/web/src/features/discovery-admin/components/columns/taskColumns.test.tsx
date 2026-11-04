import { screen, within } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import { DataTable } from "../../../../components/data-display/DataTable";
import { useLocale } from "../../../../contexts/LocaleContext";
import { emotionRules } from "../../../../test/emotionRules";
import { renderWithProviders } from "../../../../test/renderWithProviders";
import type { DiscoveryTask } from "../../types";
import { taskColumns } from "./taskColumns";

beforeEach(() => window.localStorage.setItem("locale", "en"));

const task: DiscoveryTask = {
  id: "task-1",
  catalogue_service_id: "cat-1",
  source: "pvog",
  kind: "fetch_url",
  target_url: "https://example.gov/service",
  status: "pending",
  priority: 50,
  attempt_count: 2,
  not_before: null,
  input_key: null,
  result_note: null,
  lease_expires_at: null,
  created_at: "2026-01-01T12:00:00Z",
  updated_at: "2026-01-01T12:00:00Z",
};

function Table({
  onSortChange = vi.fn(),
  items = [task],
}: {
  onSortChange?: () => void;
  items?: DiscoveryTask[];
}) {
  return (
    <DataTable
      label="Tasks"
      columns={taskColumns(useLocale())}
      rows={{ items, getKey: (item) => item.id }}
      query={{ onSortChange }}
    />
  );
}

it("task columns render every queue field of a task", () => {
  renderWithProviders(<Table onSortChange={vi.fn()} />);

  const cells = within(screen.getByRole("row", { name: /example\.gov/ }))
    .getAllByRole("cell")
    .map((cell) => cell.textContent);
  expect(cells).toEqual([
    "https://example.gov/service",
    "fetch_url",
    "Pending",
    "Portalverbund",
    "50",
    "2",
    "—",
    "—",
  ]);
});

it("task columns sort only by the keys the tasks API allowlists", async () => {
  const onSortChange = vi.fn();
  const { user } = renderWithProviders(<Table onSortChange={onSortChange} />);

  const sortable = screen.getAllByRole("button").map((b) => b.textContent);
  expect(sortable).toEqual([
    "Target URL",
    "Kind",
    "Status",
    "Source",
    "Priority",
    "Attempts",
  ]);
  await user.click(screen.getByRole("button", { name: "Priority" }));
  expect(onSortChange).toHaveBeenCalledExactlyOnceWith({
    sortBy: "priority",
    sortOrder: "asc",
  });
});

it("task columns leave the timestamp columns without sort or filter", () => {
  renderWithProviders(<Table onSortChange={vi.fn()} />);

  for (const name of ["Retry after", "Lease expires"]) {
    const header = screen.getByRole("columnheader", { name });
    expect(within(header).queryByRole("button")).not.toBeInTheDocument();
    expect(header).not.toHaveAttribute("aria-sort");
  }
});

it("task columns align priority and attempts to the end", () => {
  renderWithProviders(<Table onSortChange={vi.fn()} />);

  for (const name of [/Priority/, /Attempts/]) {
    const header = screen.getByRole("columnheader", { name });
    expect(emotionRules(header)).toContain("text-align: end");
  }
  const target = screen.getByRole("columnheader", { name: /Target/ });
  expect(emotionRules(target)).not.toContain("text-align: end");
});

it("tasks target uses the bounded cell and keeps the full URL available", async () => {
  const long = `https://example.gov/${"path/".repeat(40)}`;
  const { user } = renderWithProviders(
    <Table items={[{ ...task, target_url: long }]} />,
  );

  const target = screen.getByText(long);
  expect(emotionRules(target)).toContain("max-width: 24rem");
  expect(emotionRules(target)).toContain("text-overflow: ellipsis");
  expect(emotionRules(target.closest("td") as HTMLElement)).toContain(
    "max-width: 24rem",
  );
  await user.hover(target);
  expect(await screen.findByRole("tooltip")).toHaveTextContent(long);
});

it("task columns declare the kind, status and source filters with the translated labels", () => {
  const filters = taskColumns({ locale: "en", t: (key: string) => key })
    .flatMap((column) => (column.filter ? [column.filter] : []))
    .map(({ key, label, operators }) => ({ key, label, operators }));

  expect(filters).toEqual([
    {
      key: "kind",
      label: "discovery_admin.tasks.filter_kind",
      operators: ["eq"],
    },
    {
      key: "status",
      label: "discovery_admin.tasks.filter_status",
      operators: ["eq"],
    },
    {
      key: "source",
      label: "discovery_admin.tasks.filter_source",
      operators: ["eq"],
    },
  ]);
});

it("tasks target leaves the other task cells unbounded", () => {
  renderWithProviders(<Table />);

  const kind = screen.getByRole("cell", { name: "fetch_url" });
  expect(emotionRules(kind)).not.toContain("max-width");
});
