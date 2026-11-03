import { screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";
import QueryBoundary from "./QueryBoundary";
import type { QueryStatus } from "./queryStatus";

function status(overrides: Partial<QueryStatus> = {}): QueryStatus {
  return {
    isLoading: false,
    isRefreshing: false,
    isError: false,
    error: null,
    onRetry: vi.fn(),
    ...overrides,
  };
}

beforeEach(() => window.localStorage.setItem("locale", "en"));

it("QueryBoundary · renders children when the query is ready", () => {
  renderWithProviders(
    <QueryBoundary status={status()}>
      <div>panel-content</div>
    </QueryBoundary>,
  );

  expect(screen.getByText("panel-content")).toBeInTheDocument();
});

it("QueryBoundary · shows an announced loading note and no children while loading", () => {
  renderWithProviders(
    <QueryBoundary status={status({ isLoading: true })}>
      <div>panel-content</div>
    </QueryBoundary>,
  );

  expect(
    screen.getByRole("status", { name: "Loading..." }),
  ).toBeInTheDocument();
  expect(screen.queryByText("panel-content")).not.toBeInTheDocument();
});

it("QueryBoundary · shows retry instead of children on error and calls onRetry once", async () => {
  const onRetry = vi.fn();
  const { user } = renderWithProviders(
    <QueryBoundary status={status({ isError: true, onRetry })}>
      <div>panel-content</div>
    </QueryBoundary>,
  );

  expect(screen.queryByText("panel-content")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Try again" }));

  expect(onRetry).toHaveBeenCalledOnce();
});

it("QueryBoundary · a custom loading node replaces the default note", () => {
  renderWithProviders(
    <QueryBoundary
      status={status({ isLoading: true })}
      loading={<div>custom-skeleton</div>}
    >
      <div>panel-content</div>
    </QueryBoundary>,
  );

  expect(screen.getByText("custom-skeleton")).toBeInTheDocument();
  expect(
    screen.queryByRole("status", { name: "Loading..." }),
  ).not.toBeInTheDocument();
});
