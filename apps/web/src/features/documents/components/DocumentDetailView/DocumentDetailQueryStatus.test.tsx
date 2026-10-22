import { screen } from "@testing-library/react";
import { it, expect, vi } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import { ApiRequestError } from "../../../../services/api";
import type { QueryStatus } from "../../../../components/feedback/queryStatus";
import type { DocumentDetail } from "../../types";
import DocumentDetailQueryStatus from "./DocumentDetailQueryStatus";

const labels = {
  requirementsTitle: "Requirements",
  noRequirementsLabel: "No requirements",
  officialSourceTitle: "Official source",
};

function statusOf(overrides: Partial<QueryStatus> = {}): QueryStatus {
  return {
    isLoading: false,
    isRefreshing: false,
    isError: false,
    error: undefined,
    onRetry: vi.fn(),
    ...overrides,
  };
}

const document: DocumentDetail = {
  id: "doc-1",
  slug: "doc-1-slug",
  title: "Residency Registration",
  official_url: null,
  jurisdiction_id: "de-by-m",
  jurisdiction_path: [{ code: "de", name: "Germany", kind: "country" }],
  requirements: [],
};

it("DocumentDetailQueryStatus · loading shows skeleton not breadcrumb content", async () => {
  const { container } = renderWithProviders(
    <DocumentDetailQueryStatus
      status={statusOf({ isLoading: true })}
      content={{ document: document, ...labels }}
    />,
  );

  expect(container.querySelector(".chakra-skeleton")).toBeInTheDocument();
  expect(screen.queryByText("Germany")).not.toBeInTheDocument();
});

it("DocumentDetailQueryStatus · failure explains the problem and offers retry", async () => {
  const onRetry = vi.fn();
  const { user } = renderWithProviders(
    <DocumentDetailQueryStatus
      status={statusOf({
        isError: true,
        error: new Error("boom"),
        onRetry: onRetry,
      })}
      content={{ document: undefined, ...labels }}
    />,
  );

  expect(
    await screen.findByText("Server error. Please try again later."),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Try again" }));
  expect(onRetry).toHaveBeenCalledOnce();
});

it("DocumentDetailQueryStatus · a 404 shows a not-found state instead of an error", async () => {
  const error = new ApiRequestError({ status: 404, url: "/x", bodyText: "" });
  renderWithProviders(
    <DocumentDetailQueryStatus
      status={statusOf({ isError: true, error: error })}
      content={{ document: undefined, ...labels }}
    />,
  );

  expect(await screen.findByText("Document not found")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Try again" })).toBeNull();
});

it("DocumentDetailQueryStatus · no document without an error shows not found", async () => {
  renderWithProviders(
    <DocumentDetailQueryStatus
      status={statusOf()}
      content={{ document: undefined, ...labels }}
    />,
  );

  expect(await screen.findByText("Document not found")).toBeInTheDocument();
});

it("DocumentDetailQueryStatus · empty requirements shows empty state", async () => {
  const { container } = renderWithProviders(
    <DocumentDetailQueryStatus
      status={statusOf()}
      content={{ document: document, ...labels }}
    />,
  );

  await screen.findByText("Residency Registration");
  expect(
    container.querySelector(".chakra-empty-state__root"),
  ).toBeInTheDocument();
  const requirementsHeading = screen.getByRole("heading", {
    name: "Requirements",
  });
  expect(getComputedStyle(requirementsHeading).fontFamily).toBe(
    "var(--chakra-fonts-heading)",
  );
});

it("DocumentDetailQueryStatus · official source link renders when url present", async () => {
  renderWithProviders(
    <DocumentDetailQueryStatus
      status={statusOf()}
      content={{
        document: { ...document, official_url: "https://example.gov" },
        ...labels,
      }}
    />,
  );

  const link = await screen.findByRole("link", {
    name: "https://example.gov",
  });
  expect(link).toHaveAttribute("href", "https://example.gov");
});
