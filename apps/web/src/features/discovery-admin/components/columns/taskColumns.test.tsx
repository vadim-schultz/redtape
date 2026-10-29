import { screen, within } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import { DataTable } from "../../../../components/data-display/DataTable";
import { useLocale } from "../../../../contexts/LocaleContext";
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

function Table({ onSortChange }: { onSortChange: () => void }) {
  return (
    <DataTable
      label="Tasks"
      columns={taskColumns(useLocale())}
      rows={{ items: [task], getKey: (item) => item.id }}
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
    "pending",
    "pvog",
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
