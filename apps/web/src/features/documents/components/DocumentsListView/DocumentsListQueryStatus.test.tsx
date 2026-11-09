import { screen } from "@testing-library/react";
import { it, expect, vi } from "vitest";

import { expandControlsBesideCount } from "../../../../test/queryStatusCountRow";
import { renderWithProviders } from "../../../../test/renderWithProviders";
import type { DocumentSummary } from "../../types";
import DocumentsListQueryStatus from "./DocumentsListQueryStatus";

const documents: DocumentSummary[] = [
  {
    id: "doc-1",
    title: "Residency Registration",
    description: null,
    tags: [],
    confidence: 0.5,
  },
  {
    id: "doc-2",
    title: "Passport Renewal",
    description: null,
    tags: [],
    confidence: 0.5,
  },
];

const page = (items: DocumentSummary[]) => ({
  items,
  total: items.length,
  offset: 0,
  limit: 20,
});

it("DocumentsListQueryStatus · loading renders skeleton not cards", async () => {
  const { container } = renderWithProviders(
    <DocumentsListQueryStatus
      status={{
        isLoading: true,
        isRefreshing: false,
        isError: false,
        error: undefined,
        onRetry: vi.fn(),
      }}
      page={page(documents)}
    />,
  );

  expect(container.querySelector(".chakra-skeleton")).toBeInTheDocument();
  expect(screen.queryAllByRole("link")).toHaveLength(0);
});

it("DocumentsListQueryStatus · error explains the failure, offers retry and shows zero cards", async () => {
  const onRetry = vi.fn();
  const { user } = renderWithProviders(
    <DocumentsListQueryStatus
      status={{
        isLoading: false,
        isRefreshing: false,
        isError: true,
        error: new Error("boom"),
        onRetry,
      }}
      page={undefined}
    />,
  );

  expect(
    await screen.findByText("Server error. Please try again later."),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Try again" }));
  expect(onRetry).toHaveBeenCalledOnce();
  expect(screen.queryAllByRole("link")).toHaveLength(0);
});

it("DocumentsListQueryStatus · empty list renders an empty state with guidance", async () => {
  renderWithProviders(
    <DocumentsListQueryStatus
      status={{
        isLoading: false,
        isRefreshing: false,
        isError: false,
        error: undefined,
        onRetry: vi.fn(),
      }}
      page={page([])}
    />,
  );

  expect(screen.getByRole("status")).toHaveTextContent("No documents found");
  expect(
    screen.getByText("No documents have been found yet."),
  ).toBeInTheDocument();
  expect(screen.queryAllByRole("link")).toHaveLength(0);
});

it("DocumentsListQueryStatus · populated count row has no expand control", async () => {
  renderWithProviders(
    <DocumentsListQueryStatus
      status={{
        isLoading: false,
        isRefreshing: false,
        isError: false,
        error: undefined,
        onRetry: vi.fn(),
      }}
      page={page(documents)}
    />,
  );

  const countLabel = await screen.findByTestId("query-status-count");
  expect(countLabel).toHaveTextContent("2 documents");
  expect(expandControlsBesideCount(countLabel)).toHaveLength(0);
  expect(screen.getAllByRole("link")).toHaveLength(2);
});

it("DocumentsListQueryStatus · populated list renders count and cards", async () => {
  renderWithProviders(
    <DocumentsListQueryStatus
      status={{
        isLoading: false,
        isRefreshing: false,
        isError: false,
        error: undefined,
        onRetry: vi.fn(),
      }}
      page={page(documents)}
    />,
  );

  expect(await screen.findByText("2 documents")).toBeInTheDocument();
  expect(screen.getAllByRole("link")).toHaveLength(2);
});

it("DocumentsListQueryStatus · refreshing keeps the cards, dims them and marks the list busy", async () => {
  renderWithProviders(
    <DocumentsListQueryStatus
      status={{
        isLoading: false,
        isRefreshing: true,
        isError: false,
        error: undefined,
        onRetry: vi.fn(),
      }}
      page={page(documents)}
    />,
  );

  const list = (await screen.findAllByRole("link"))[0].closest("[aria-busy]");
  expect(screen.getAllByRole("link")).toHaveLength(2);
  expect(list).toHaveAttribute("aria-busy", "true");
  expect(getComputedStyle(list as Element).opacity).toBe("0.6");
});

it("DocumentsListQueryStatus · singular count reads naturally", async () => {
  window.localStorage.setItem("locale", "de");
  renderWithProviders(
    <DocumentsListQueryStatus
      status={{
        isLoading: false,
        isRefreshing: false,
        isError: false,
        error: undefined,
        onRetry: vi.fn(),
      }}
      page={page([documents[0]])}
    />,
  );

  expect(await screen.findByText("1 Dokument")).toBeInTheDocument();
});
