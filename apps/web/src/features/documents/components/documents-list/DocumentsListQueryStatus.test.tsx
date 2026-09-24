import { screen } from "@testing-library/react";
import { it, expect } from "vitest";

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
      listTitleLabel="documents"
      documents={documents}
    />,
  );

  expect(container.querySelector(".chakra-skeleton")).toBeInTheDocument();
  expect(screen.queryAllByRole("link")).toHaveLength(0);
});

it("DocumentsListQueryStatus · error renders alert and zero cards", async () => {
  const { container } = renderWithProviders(
    <DocumentsListQueryStatus
      isLoading={false}
      isError
      error={new Error("boom")}
      listTitleLabel="documents"
      documents={undefined}
    />,
  );

  expect(container.querySelector(".chakra-alert__root")).toBeInTheDocument();
  expect(await screen.findByText("Server error")).toBeInTheDocument();
  expect(screen.queryAllByRole("link")).toHaveLength(0);
});
