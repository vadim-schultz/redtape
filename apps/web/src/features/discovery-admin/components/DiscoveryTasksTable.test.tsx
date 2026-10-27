import { screen, within } from "@testing-library/react";
import { expect, it } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import type { DiscoveryTask } from "../types";
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

function inHours(hours: number): string {
  return new Date(Date.now() + hours * HOUR_MS).toISOString();
}

function rowOf(url: string): HTMLElement {
  return screen.getByText(url).closest("tr") as HTMLElement;
}

it("DiscoveryTasksTable · shows kind, attempts and a retry-after cell for a delayed task", () => {
  renderWithProviders(
    <DiscoveryTasksTable
      tasks={[
        task({
          target_url: "https://example.gov/delayed",
          attempt_count: 2,
          not_before: inHours(3.5),
        }),
      ]}
    />,
  );

  const cells = within(rowOf("https://example.gov/delayed")).getAllByRole(
    "cell",
  );
  const texts = cells.map((cell) => cell.textContent);
  expect(texts).toContain("harvest_payload");
  expect(texts).toContain("2");
  expect(texts).toContain("in 3 hours");
});

it("DiscoveryTasksTable · leaves the retry-after cell empty unless not_before is in the future", () => {
  renderWithProviders(
    <DiscoveryTasksTable
      tasks={[
        task({ id: "a", target_url: "https://example.gov/fresh" }),
        task({
          id: "b",
          target_url: "https://example.gov/due",
          attempt_count: 1,
          not_before: inHours(-2),
        }),
      ]}
    />,
  );

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
  renderWithProviders(
    <DiscoveryTasksTable
      tasks={[
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
      ]}
    />,
  );

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
  renderWithProviders(
    <DiscoveryTasksTable
      tasks={[task({ target_url: "https://example.gov/plain" })]}
    />,
  );

  expect(
    statusCellOf("https://example.gov/plain").querySelector(".chakra-badge"),
  ).toBeNull();
});

it("tasks table labels result notes in German", () => {
  window.localStorage.setItem("locale", "de");
  renderWithProviders(
    <DiscoveryTasksTable
      tasks={[task({ status: "completed", result_note: "oversize" })]}
    />,
  );

  expect(screen.getByText("Zu groß")).toBeInTheDocument();
});
