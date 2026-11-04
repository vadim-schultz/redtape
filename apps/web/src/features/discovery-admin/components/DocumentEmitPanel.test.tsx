import { screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import type { QueryStatus } from "../../../components/feedback/queryStatus";
import { renderWithProviders } from "../../../test/renderWithProviders";
import type { CandidateEmitPreview } from "../types";
import DocumentEmitPanel from "./DocumentEmitPanel";

beforeEach(() => window.localStorage.setItem("locale", "en"));

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

const preview: CandidateEmitPreview = {
  candidate_id: "cand-1",
  suggestion: {
    kind: "document",
    jurisdiction_id: "de",
    source_url: "https://example.gov/doc",
    payload: { title_i18n: { en: "ID card" } },
  },
  suggestion_id: null,
  skip_reason: null,
  conflicts: [],
};

it("DocumentEmitPanel · shows the preview when loaded", () => {
  renderWithProviders(
    <DocumentEmitPanel
      status={status()}
      preview={preview}
      suggestionId={null}
    />,
  );

  expect(screen.getByText("ID card")).toBeInTheDocument();
  expect(
    screen.getByText("Emitting is done from the command line, not here."),
  ).toBeInTheDocument();
});

it("DocumentEmitPanel · emitted candidate shows the emitted state and no loading or CLI hint", () => {
  renderWithProviders(
    <DocumentEmitPanel
      status={status({ isLoading: true })}
      preview={undefined}
      suggestionId="sug-1"
    />,
  );

  expect(screen.getByText("sug-1")).toBeInTheDocument();
  expect(screen.queryByRole("status")).not.toBeInTheDocument();
  expect(
    screen.queryByText("Emitting is done from the command line, not here."),
  ).not.toBeInTheDocument();
});

it("DocumentEmitPanel · error shows retry and calls onRetry", async () => {
  const onRetry = vi.fn();
  const { user } = renderWithProviders(
    <DocumentEmitPanel
      status={status({ isError: true, onRetry })}
      preview={undefined}
      suggestionId={null}
    />,
  );

  await user.click(screen.getByRole("button", { name: "Try again" }));

  expect(onRetry).toHaveBeenCalledOnce();
});
