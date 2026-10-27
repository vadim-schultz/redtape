import { screen, within } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import type { QueryStatus } from "../../../components/feedback/queryStatus";
import { renderWithProviders } from "../../../test/renderWithProviders";
import type { DiscoveryArtifact } from "../types";
import ArtifactsPanel from "./ArtifactsPanel";

const READY: QueryStatus = {
  isLoading: false,
  isRefreshing: false,
  isError: false,
  error: null,
  onRetry: () => undefined,
};

function artifact(overrides: Partial<DiscoveryArtifact>): DiscoveryArtifact {
  return {
    id: "art-1",
    catalogue_service_id: "cat-1",
    discovery_task_id: "task-1",
    kind: "screenshot",
    content_type: "image/png",
    byte_size: 2048,
    source_url: "https://example.gov/service",
    final_url: "https://www.example.gov/service?x=1",
    fetched_at: "2026-10-26T12:00:00Z",
    created_at: "2026-10-26T12:00:00Z",
    url: "https://store.example/shot.png?sig=abc",
    ...overrides,
  };
}

function snapshot(overrides: Partial<DiscoveryArtifact> = {}) {
  return artifact({
    id: "art-2",
    kind: "html_snapshot",
    content_type: "text/html",
    byte_size: 1536,
    url: "https://store.example/page.html?sig=def",
    ...overrides,
  });
}

function renderPanel(
  artifacts: DiscoveryArtifact[] | undefined,
  status: Partial<QueryStatus> = {},
) {
  return renderWithProviders(
    <ArtifactsPanel status={{ ...READY, ...status }} artifacts={artifacts} />,
  );
}

beforeEach(() => window.localStorage.setItem("locale", "en"));

it("artifacts panel shows a screenshot thumbnail with alt text and a new-tab link", () => {
  renderPanel([artifact({})]);

  const image = screen.getByRole("img", {
    name: "Screenshot captured on Oct 26, 2026",
  });
  expect(image).toHaveAttribute(
    "src",
    "https://store.example/shot.png?sig=abc",
  );
  expect(image).toHaveAttribute("loading", "lazy");
  const link = image.closest("a");
  expect(link).toHaveAttribute(
    "href",
    "https://store.example/shot.png?sig=abc",
  );
  expect(link).toHaveAttribute("target", "_blank");
  expect(link).toHaveAttribute("rel", "noopener noreferrer");
});

it("artifacts panel shows no thumbnail or link for a screenshot without a url", () => {
  renderPanel([artifact({ url: null }), artifact({ id: "art-3" })]);

  expect(screen.getAllByRole("img")).toHaveLength(1);
  expect(screen.getByText("Link unavailable")).toBeInTheDocument();
});

it("artifacts panel shows a download link for an html snapshot and never renders it inline", () => {
  const { container } = renderPanel([
    snapshot({ source_url: "https://example.gov/<script>alert(1)</script>" }),
  ]);

  const row = screen.getByText(
    /1\.5 KB, fetched Oct 26, 2026, www\.example\.gov/,
  );
  const link = within(row.closest("li") as HTMLElement).getByRole("link", {
    name: "Download",
  });
  expect(link).toHaveAttribute(
    "href",
    "https://store.example/page.html?sig=def",
  );
  expect(link).toHaveAttribute("rel", "noopener noreferrer");
  expect(container.querySelector("iframe")).toBeNull();
  expect(container.innerHTML).not.toContain("alert(1)");
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
});

it("artifacts panel shows the empty state and the error state", () => {
  const onRetry = vi.fn();
  const { rerender } = renderPanel([]);
  expect(screen.getByText("No artifacts yet.")).toBeInTheDocument();

  rerender(
    <ArtifactsPanel
      status={{ ...READY, isError: true, onRetry }}
      artifacts={undefined}
    />,
  );
  expect(screen.queryByText("No artifacts yet.")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
});

it("artifacts panel shows a loading skeleton while the query loads", () => {
  renderPanel(undefined, { isLoading: true });

  expect(
    screen.getByRole("status", { name: "Loading..." }),
  ).toBeInTheDocument();
  expect(screen.queryByText("No artifacts yet.")).not.toBeInTheDocument();
});

it("artifacts panel shows the storage-not-configured message when urls are null", () => {
  renderPanel([artifact({ url: null }), snapshot({ url: null })]);

  expect(
    screen.getByText(/Artifact storage is not configured/),
  ).toBeInTheDocument();
  expect(screen.queryByRole("link")).not.toBeInTheDocument();
});

it("artifacts panel keeps the sections apart and tolerates an unknown kind", () => {
  renderPanel([
    artifact({}),
    snapshot(),
    snapshot({ id: "art-9", kind: "pdf_copy" as DiscoveryArtifact["kind"] }),
  ]);

  expect(
    screen.queryByText(/Artifact storage is not configured/),
  ).not.toBeInTheDocument();
  expect(screen.getByText("Screenshots")).toBeInTheDocument();
  expect(screen.getByText("HTML snapshots")).toBeInTheDocument();
  expect(screen.getByText("pdf_copy")).toBeInTheDocument();
});
