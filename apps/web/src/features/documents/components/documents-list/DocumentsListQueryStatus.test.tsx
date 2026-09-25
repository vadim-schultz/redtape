import { screen } from "@testing-library/react";
import { it, expect, vi } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import type { DocumentSummary } from "../../types";
import DocumentsListQueryStatus from "./DocumentsListQueryStatus";

const documents: DocumentSummary[] = [
  { id: "doc-1", slug: "doc-1-slug", title: "Residency Registration" },
  { id: "doc-2", slug: "doc-2-slug", title: "Passport Renewal" },
];

it("DocumentsListQueryStatus · loading renders skeleton not cards", async () => {
  const { container } = renderWithProviders(
    <DocumentsListQueryStatus
      isLoading
      isError={false}
      error={undefined}
      onRetry={vi.fn()}
      isRefreshing={false}
      listTitleLabel="documents"
      documents={documents}
    />,
  );

  expect(container.querySelector(".chakra-skeleton")).toBeInTheDocument();
  expect(screen.queryAllByRole("link")).toHaveLength(0);
});

it("DocumentsListQueryStatus · error explains the failure, offers retry and shows zero cards", async () => {
  const onRetry = vi.fn();
  const { user } = renderWithProviders(
    <DocumentsListQueryStatus
      isLoading={false}
      isError
      error={new Error("boom")}
      onRetry={onRetry}
      isRefreshing={false}
      listTitleLabel="documents"
      documents={undefined}
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
      isLoading={false}
      isError={false}
      error={undefined}
      onRetry={vi.fn()}
      isRefreshing={false}
      listTitleLabel="documents"
      documents={[]}
    />,
  );

  expect(screen.getByRole("status")).toHaveTextContent("No documents found");
  expect(
    screen.getByText("Try selecting a different location."),
  ).toBeInTheDocument();
  expect(screen.queryAllByRole("link")).toHaveLength(0);
});

it("DocumentsListQueryStatus · populated list renders count and cards", async () => {
  renderWithProviders(
    <DocumentsListQueryStatus
      isLoading={false}
      isError={false}
      error={undefined}
      onRetry={vi.fn()}
      isRefreshing={false}
      listTitleLabel="documents"
      documents={documents}
    />,
  );

  expect(await screen.findByText("2 documents")).toBeInTheDocument();
  expect(screen.getAllByRole("link")).toHaveLength(2);
});

it("DocumentsListQueryStatus · refreshing keeps the cards, dims them and marks the list busy", async () => {
  renderWithProviders(
    <DocumentsListQueryStatus
      isLoading={false}
      isRefreshing
      isError={false}
      error={undefined}
      onRetry={vi.fn()}
      listTitleLabel="documents"
      documents={documents}
    />,
  );

  const list = (await screen.findAllByRole("link"))[0].parentElement;
  expect(screen.getAllByRole("link")).toHaveLength(2);
  expect(list).toHaveAttribute("aria-busy", "true");
  expect(getComputedStyle(list as Element).opacity).toBe("0.6");
});
