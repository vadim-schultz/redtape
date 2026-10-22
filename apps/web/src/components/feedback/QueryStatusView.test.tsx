import { screen } from "@testing-library/react";
import { it, expect, vi } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";
import { expandControlsBesideCount } from "../../test/queryStatusCountRow";
import QueryStatusView from "./QueryStatusView";

type Item = { id: string; label: string };

const items: Item[] = [
  { id: "1", label: "One" },
  { id: "2", label: "Two" },
];

const slots = {
  getKey: (item: Item) => item.id,
  renderItem: (item: Item) => <a href={`/items/${item.id}`}>{item.label}</a>,
  renderSkeleton: () => <div data-testid="skeleton" />,
  renderEmpty: () => <div role="status">Nothing here</div>,
  countLabel: (count: number) => `${count} items`,
};

it("QueryStatusView · loading renders the skeleton, not items", () => {
  renderWithProviders(
    <QueryStatusView
      slots={slots}
      status={{
        isLoading: true,
        isRefreshing: false,
        isError: false,
        error: undefined,
        onRetry: vi.fn(),
      }}
      items={items}
    />,
  );

  expect(screen.getByTestId("skeleton")).toBeInTheDocument();
  expect(screen.queryAllByRole("link")).toHaveLength(0);
});

it("QueryStatusView · error offers retry and shows zero items", async () => {
  const onRetry = vi.fn();
  const { user } = renderWithProviders(
    <QueryStatusView
      slots={slots}
      status={{
        isLoading: false,
        isRefreshing: false,
        isError: true,
        error: new Error("boom"),
        onRetry,
      }}
      items={undefined}
    />,
  );

  expect(
    await screen.findByText("Server error. Please try again later."),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Try again" }));
  expect(onRetry).toHaveBeenCalledOnce();
});

it("QueryStatusView · empty renders the caller's empty state", () => {
  renderWithProviders(
    <QueryStatusView
      slots={slots}
      status={{
        isLoading: false,
        isRefreshing: false,
        isError: false,
        error: undefined,
        onRetry: vi.fn(),
      }}
      items={[]}
    />,
  );

  expect(screen.getByText("Nothing here")).toBeInTheDocument();
});

it("QueryStatusView · populated count row has no expand control", async () => {
  const { container } = renderWithProviders(
    <QueryStatusView
      slots={slots}
      status={{
        isLoading: false,
        isRefreshing: false,
        isError: false,
        error: undefined,
        onRetry: vi.fn(),
      }}
      items={items}
    />,
  );

  const countLabel = await screen.findByTestId("query-status-count");
  expect(countLabel).toHaveTextContent("2 items");
  expect(expandControlsBesideCount(countLabel)).toHaveLength(0);
  expect(screen.getAllByRole("link")).toHaveLength(2);
  expect(
    container.querySelector('[data-testid="query-status-count-row"] svg'),
  ).toBeNull();
});

it("QueryStatusView · populated renders the count label and each item", async () => {
  renderWithProviders(
    <QueryStatusView
      slots={slots}
      status={{
        isLoading: false,
        isRefreshing: false,
        isError: false,
        error: undefined,
        onRetry: vi.fn(),
      }}
      items={items}
    />,
  );

  expect(await screen.findByText("2 items")).toBeInTheDocument();
  expect(screen.getAllByRole("link")).toHaveLength(2);
});

it("QueryStatusView · refreshing keeps items visible, dims and marks the list busy", async () => {
  renderWithProviders(
    <QueryStatusView
      slots={slots}
      status={{
        isLoading: false,
        isRefreshing: true,
        isError: false,
        error: undefined,
        onRetry: vi.fn(),
      }}
      items={items}
    />,
  );

  const list = (await screen.findAllByRole("link"))[0].parentElement;
  expect(list).toHaveAttribute("aria-busy", "true");
  expect(getComputedStyle(list as Element).opacity).toBe("0.6");
});
