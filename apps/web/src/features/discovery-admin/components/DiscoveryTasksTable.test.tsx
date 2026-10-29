import { screen, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import type { QueryStatus } from "../../../components/feedback/queryStatus";
import { fakeListController } from "../../../test/fakeListController";
import { renderWithProviders } from "../../../test/renderWithProviders";
import type { DiscoveryTask, TaskFilterKey, TaskSortKey } from "../types";
import DiscoveryTasksTable from "./DiscoveryTasksTable";

const HOUR_MS = 3_600_000;

function task(overrides: Partial<DiscoveryTask>): DiscoveryTask {
  return {
    id: "task-1",
    catalogue_service_id: "cat-1",
    source: "pvog",
    kind: "harvest_payload",
    target_url: "https://example.gov/service",
    status: "pending",
    priority: 50,
    attempt_count: 0,
    not_before: null,
    input_key: null,
    result_note: null,
    lease_expires_at: null,
    created_at: "2026-01-01T12:00:00Z",
    updated_at: "2026-01-01T12:00:00Z",
    ...overrides,
  };
}

const READY: QueryStatus = {
  isLoading: false,
  isRefreshing: false,
  isError: false,
  error: null,
  onRetry: vi.fn(),
};

const fakeList = () => fakeListController<TaskSortKey, TaskFilterKey>();

function renderTable(tasks: DiscoveryTask[], total = tasks.length) {
  return renderWithProviders(
    <DiscoveryTasksTable
      status={READY}
      page={{ items: tasks, total, offset: 0, limit: 20 }}
      list={fakeList()}
    />,
  );
}

function inHours(hours: number): string {
  return new Date(Date.now() + hours * HOUR_MS).toISOString();
}

function rowOf(url: string): HTMLElement {
  return screen.getByText(url).closest("tr") as HTMLElement;
}

it("DiscoveryTasksTable · shows kind, attempts and a retry-after cell for a delayed task", () => {
  renderTable([
    task({
      target_url: "https://example.gov/delayed",
      attempt_count: 2,
      not_before: inHours(3.5),
    }),
  ]);

  const cells = within(rowOf("https://example.gov/delayed")).getAllByRole(
    "cell",
  );
  const texts = cells.map((cell) => cell.textContent);
  expect(texts).toContain("harvest_payload");
  expect(texts).toContain("2");
  expect(texts).toContain("in 3 hours");
});

it("DiscoveryTasksTable · leaves the retry-after cell empty unless not_before is in the future", () => {
  renderTable([
    task({ id: "a", target_url: "https://example.gov/fresh" }),
    task({
      id: "b",
      target_url: "https://example.gov/due",
      attempt_count: 1,
      not_before: inHours(-2),
    }),
  ]);

  for (const url of ["https://example.gov/fresh", "https://example.gov/due"]) {
    const texts = within(rowOf(url))
      .getAllByRole("cell")
      .map((cell) => cell.textContent);
    expect(texts.filter((text) => text?.startsWith("in "))).toEqual([]);
    expect(texts.at(-1)).toBe("—");
  }
});

function statusCellOf(url: string): HTMLElement {
  return within(rowOf(url)).getAllByRole("cell")[2];
}

it("tasks table shows the render_page kind and a result_note chip, and falls back to the raw value for an unknown note", () => {
  renderTable([
    task({
      id: "a",
      target_url: "https://example.gov/walled",
      kind: "render_page",
      status: "completed",
      result_note: "login_wall",
    }),
    task({
      id: "b",
      target_url: "https://example.gov/odd",
      status: "completed",
      result_note: "brand_new_note",
    }),
  ]);

  const walled = within(rowOf("https://example.gov/walled"));
  expect(walled.getByText("render_page")).toBeInTheDocument();
  expect(
    within(statusCellOf("https://example.gov/walled")).getByText("Login wall"),
  ).toHaveClass("chakra-badge");
  expect(
    within(statusCellOf("https://example.gov/odd")).getByText("brand_new_note"),
  ).toHaveClass("chakra-badge");
});

it("tasks table shows no note chip for a task without a result_note", () => {
  renderTable([task({ target_url: "https://example.gov/plain" })]);

  expect(
    statusCellOf("https://example.gov/plain").querySelector(".chakra-badge"),
  ).toBeNull();
});

it("tasks table labels result notes in German", () => {
  window.localStorage.setItem("locale", "de");
  renderTable([task({ status: "completed", result_note: "oversize" })]);

  expect(screen.getByText("Zu groß")).toBeInTheDocument();
});

it("tasks table shows the llm_extract kind and translates its result notes, leaving the counts note raw", () => {
  renderTable([
    task({
      id: "a",
      target_url: "https://example.gov/empty",
      kind: "llm_extract",
      status: "completed",
      result_note: "no_content",
    }),
    task({
      id: "b",
      target_url: "https://example.gov/none",
      kind: "llm_extract",
      status: "completed",
      result_note: "no_documents",
    }),
    task({
      id: "c",
      target_url: "https://example.gov/done",
      kind: "llm_extract",
      status: "completed",
      result_note: "docs=7 edges=5 dropped=2",
    }),
  ]);

  expect(
    within(statusCellOf("https://example.gov/empty")).getByText("No content"),
  ).toHaveClass("chakra-badge");
  expect(
    within(statusCellOf("https://example.gov/none")).getByText("No documents"),
  ).toBeInTheDocument();
  expect(
    within(statusCellOf("https://example.gov/done")).getByText(
      "docs=7 edges=5 dropped=2",
    ),
  ).toBeInTheDocument();
});

it("discovery tasks render response rows and total count", async () => {
  const list = fakeList();
  const { user } = renderWithProviders(
    <DiscoveryTasksTable
      status={READY}
      page={{
        items: [task({ id: "a" }), task({ id: "b", target_url: "https://b" })],
        total: 45,
        offset: 0,
        limit: 20,
      }}
      list={list}
    />,
  );

  const table = screen.getByRole("table", { name: "Crawler tasks" });
  expect(table.closest("[data-section-card]")).not.toBeNull();
  expect(screen.getByText("45 tasks")).toBeInTheDocument();
  expect(screen.queryByText("2 tasks")).not.toBeInTheDocument();
  expect(screen.getByText("1–20 of 45")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Next page" }));
  expect(list.setOffset).toHaveBeenCalledExactlyOnceWith(20);
});

it("a failed refetch keeps the previous rows, the total and a retry", async () => {
  const onRetry = vi.fn();
  const { user } = renderWithProviders(
    <DiscoveryTasksTable
      status={{ ...READY, isError: true, onRetry }}
      page={{
        items: [task({ target_url: "https://previous" })],
        total: 1,
        offset: 0,
        limit: 20,
      }}
      list={fakeList()}
    />,
  );

  expect(screen.getByText("https://previous")).toBeVisible();
  expect(screen.getByText("1 task")).toBeVisible();
  expect(screen.getByRole("alert")).toHaveTextContent("Could not refresh");
  await user.click(screen.getByRole("button", { name: "Try again" }));
  expect(onRetry).toHaveBeenCalledOnce();
});

it("a first-load failure shows the retryable error and no rows or count", async () => {
  const onRetry = vi.fn();
  const { user } = renderWithProviders(
    <DiscoveryTasksTable
      status={{ ...READY, isError: true, onRetry }}
      page={undefined}
      list={fakeList()}
    />,
  );

  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  expect(screen.queryByText(/tasks?$/)).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Try again" }));
  expect(onRetry).toHaveBeenCalledOnce();
});

it("tasks table shows the empty state without a count or paging", () => {
  renderTable([]);

  expect(screen.getByText("No tasks in queue")).toBeInTheDocument();
  expect(screen.queryByText(/tasks?$/)).not.toBeInTheDocument();
  expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
});

it("tasks table sorts and filters through the list controller", async () => {
  const list = fakeList();
  const { user } = renderWithProviders(
    <DiscoveryTasksTable
      status={READY}
      page={{ items: [task({})], total: 1, offset: 0, limit: 20 }}
      list={list}
    />,
  );

  await user.click(screen.getByRole("button", { name: "Attempts" }));
  expect(list.setSort).toHaveBeenCalledExactlyOnceWith({
    sortBy: "attempts",
    sortOrder: "asc",
  });
  await user.click(screen.getByRole("button", { name: "Task status" }));
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Task status" }),
    "failed",
  );
  await user.click(screen.getByRole("button", { name: "Apply" }));
  expect(list.setFilter).toHaveBeenCalledExactlyOnceWith("status", "failed");
});
