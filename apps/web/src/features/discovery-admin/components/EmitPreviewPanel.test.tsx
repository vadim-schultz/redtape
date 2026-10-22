import { screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import type { QueryStatus } from "../../../components/feedback/queryStatus";
import { renderWithProviders } from "../../../test/renderWithProviders";
import type { EmitPreviewItem } from "../types";
import EmitPreviewPanel from "./EmitPreviewPanel";

const items: EmitPreviewItem[] = [
  {
    claim_id: "claim-1",
    kind: "new_document",
    payload: { kind: "new_document" },
    skip_reason: null,
  },
  {
    claim_id: "claim-2",
    kind: "new_requirement",
    payload: null,
    skip_reason: "unresolved_requirement_documents",
  },
];

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

function renderPanel(
  state: QueryStatus,
  data: EmitPreviewItem[] | undefined = items,
) {
  const fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  return {
    fetchMock,
    ...renderWithProviders(<EmitPreviewPanel status={state} items={data} />),
  };
}

it("EmitPreviewPanel · lists the preview rows it is given", () => {
  renderPanel(status());

  expect(screen.getByText("new_document")).toBeInTheDocument();
  expect(
    screen.getByText(/unresolved_requirement_documents/),
  ).toBeInTheDocument();
});

it("EmitPreviewPanel · shows the empty note when there are no rows", () => {
  renderPanel(status(), []);

  expect(
    screen.getByText("No claims to preview yet."),
  ).toBeInTheDocument();
});

it("EmitPreviewPanel · error shows retry, which calls onRetry and no API", async () => {
  const onRetry = vi.fn();
  const { user, fetchMock } = renderPanel(
    status({ isError: true, onRetry }),
    undefined,
  );

  await user.click(screen.getByRole("button", { name: /try again/i }));

  expect(onRetry).toHaveBeenCalledTimes(1);
  expect(screen.queryByText("new_document")).toBeNull();
  expect(fetchMock).not.toHaveBeenCalledWith(
    expect.stringContaining("emit-preview"),
    expect.anything(),
  );
});
